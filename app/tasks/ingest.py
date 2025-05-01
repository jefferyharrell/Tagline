import logging

# Import necessary components for media processing
from app.db.repositories.media_object import MediaObjectRepository

# Import processor modules to trigger registration via decorators
# The noqa comment prevents linters from flagging unused import, which is needed here.
from app.media_processing import heicprocessor  # noqa: F401
from app.media_processing import jpegprocessor  # noqa: F401
from app.media_processing.factory import get_processor
from app.storage_types import MediaObject

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
        else:
            logger.warning(
                f"Processor {type(processor).__name__} returned empty intrinsic metadata for "
                f"{media_object.object_key}."
            )

    except NotImplementedError:
        logger.warning(
            f"No processor found for mimetype '{(media_object.metadata or {}).get('mimetype')}' "
            f"on object {media_object.object_key}. Skipping intrinsic metadata extraction."
        )
        # Continue without intrinsic metadata
        pass

    except Exception as e:
        # Log other processing errors but attempt to commit basic info anyway
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
        db_obj = repo.create(media_object)

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
