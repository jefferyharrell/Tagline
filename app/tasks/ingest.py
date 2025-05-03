import logging

# Import necessary components for media processing
from app.db.repositories.media_object import MediaObjectRepository
from app.domain_media_object import MediaObjectRecord

# Import processor modules to trigger registration via decorators
# The noqa comment prevents linters from flagging unused import, which is needed here.
from app.media_processing import heicprocessor  # noqa: F401
from app.media_processing import jpegprocessor  # noqa: F401
from app.media_processing.factory import get_processor
from app.schemas import MediaObject

logger = logging.getLogger(__name__)


# TODO: Add `intrinsic_metadata` field to MediaObject model and repository update method
async def ingest(media_object: MediaObject) -> bool:
    """Processes a single media object: extracts metadata and commits to DB."""
    logger.info(f"Starting processing for media object: {media_object.object_key}")
    intrinsic_metadata = {}

    try:
        # 1. Try to get the appropriate processor
        processor = get_processor(media_object)

        # 2. Extract intrinsic metadata if processor found
        intrinsic_metadata = await processor.extract_intrinsic_metadata()
        if intrinsic_metadata:
            logger.info(
                f"Extracted intrinsic metadata for {media_object.object_key}: "
                f"{intrinsic_metadata}"
            )
            # Update the metadata on the Pydantic object before saving
            media_object.metadata = (
                media_object.metadata or {}
            )  # Ensure metadata dict exists
            media_object.metadata["intrinsic"] = intrinsic_metadata
        else:
            logger.warning(
                f"No intrinsic metadata extracted for {media_object.object_key}"
            )

        # 3. Generate and save thumbnail (safely)
        try:
            content = await processor.get_content()
            thumbnail_result = await processor.generate_thumbnail(content)
            if thumbnail_result:
                thumbnail_bytes, thumbnail_mimetype = thumbnail_result
                logger.info(
                    f"Generated thumbnail for {media_object.object_key} with mimetype {thumbnail_mimetype}"
                )
            else:
                thumbnail_bytes = None
                thumbnail_mimetype = None
        except Exception as thumb_exc:
            logger.warning(
                f"Failed to generate thumbnail for {media_object.object_key}: {thumb_exc}",
                exc_info=True,  # Log traceback for debugging
            )
            thumbnail_bytes = None  # Ensure it's None on failure
            thumbnail_mimetype = None

        # 4. Get or create the MediaObject record in the database
        repo = MediaObjectRepository()
        domain_record = MediaObjectRecord.from_pydantic(media_object)
        db_media_object = repo.get_or_create(domain_record)

        if not db_media_object:
            logger.error(
                f"Failed to commit MediaObject via repository for key: {media_object.object_key}"
            )
            return False  # Indicate failure

        # 5. Update thumbnail if generated successfully
        if thumbnail_bytes and thumbnail_mimetype:
            if not repo.update_thumbnail(
                media_object.object_key, thumbnail_bytes, thumbnail_mimetype
            ):
                logger.error(
                    f"Failed to update thumbnail for {media_object.object_key}"
                )
                # Decide if this is a critical failure or just a warning

        logger.info(
            f"Successfully processed and committed {media_object.object_key}"
            + (" with" if intrinsic_metadata else " without")
            + " intrinsic metadata."
        )
        return True  # Indicate success

    except Exception as e:
        logger.exception(
            f"Error during intrinsic metadata extraction for {media_object.object_key}: {e}"
        )
        # Continue without intrinsic metadata
        pass

    # 3. Use repository to commit/update the database object
    try:
        repo = MediaObjectRepository()

        # Placeholder: Merge intrinsic metadata into the main metadata dictionary.
        # A dedicated DB field (e.g., JSONB) is the proper long-term solution.
        if media_object.metadata is None:
            media_object.metadata = {}

        # Only add intrinsic key if metadata was extracted
        if intrinsic_metadata:
            media_object.metadata["intrinsic"] = intrinsic_metadata
        # Else: Commit the object with potentially only the original metadata

        # Commit the object (create or update)
        # Assuming repo.create handles potential updates or has get_or_create logic
        domain_record = MediaObjectRecord.from_pydantic(media_object)
        db_obj = repo.create(domain_record)

        if not db_obj:
            logger.error(
                f"Failed to commit MediaObject via repository for key: {media_object.object_key}"
            )
            return False  # Indicate failure

        logger.info(
            f"Successfully processed and committed {media_object.object_key}"
            + (" with" if intrinsic_metadata else " without")
            + " intrinsic metadata."
        )
        return True  # Indicate success

    except Exception as e:
        logger.exception(
            f"Error committing media object {media_object.object_key} to DB: {e}"
        )
        return False  # Indicate failure
