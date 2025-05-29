import logging

# Import necessary components for media processing
from app.config import get_settings
from app.db.database import get_db
from app.db.repositories.media_object import MediaObjectRepository
from app.domain_media_object import MediaObjectRecord

# Import processor modules to trigger registration via decorators
# The noqa comment prevents linters from flagging unused import, which is needed here.
from app.media_processing import heicprocessor  # noqa: F401
from app.media_processing import jpegprocessor  # noqa: F401
from app.media_processing.factory import get_processor
from app.s3_binary_storage import S3BinaryStorage, S3Config
from app.schemas import StoredMediaObject

logger = logging.getLogger(__name__)


# TODO: Add `intrinsic_metadata` field to MediaObject model and repository update method
async def ingest(stored_media_object: StoredMediaObject) -> bool:
    """Processes a single stored media object: extracts metadata and commits to DB."""
    logger.info(
        f"Starting processing for stored media object: {stored_media_object.object_key}"
    )
    intrinsic_metadata = {}

    # Convert to domain record for further processing
    domain_record = MediaObjectRecord.from_stored(stored_media_object)

    # Create a database session for this task
    db_gen = get_db()
    db = next(db_gen)

    try:
        repo = MediaObjectRepository(db)

        # Initialize S3 storage (required)
        settings = get_settings()
        if not all(
            [
                settings.S3_ENDPOINT_URL,
                settings.S3_ACCESS_KEY_ID,
                settings.S3_SECRET_ACCESS_KEY,
                settings.S3_BUCKET_NAME,
            ]
        ):
            logger.error(
                "S3 configuration is incomplete. S3 storage is required for Tagline."
            )
            return False

        config = S3Config(
            endpoint_url=settings.S3_ENDPOINT_URL,  # type: ignore[arg-type]
            access_key_id=settings.S3_ACCESS_KEY_ID,  # type: ignore[arg-type]
            secret_access_key=settings.S3_SECRET_ACCESS_KEY,  # type: ignore[arg-type]
            bucket_name=settings.S3_BUCKET_NAME,  # type: ignore[arg-type]
            region=settings.S3_REGION,
        )
        s3_storage = S3BinaryStorage(config)

        # Use domain_record for downstream logic
        try:
            # 1. Try to get the appropriate processor
            processor = get_processor(stored_media_object)

            # 2. Extract intrinsic metadata if processor found
            intrinsic_metadata = await processor.extract_intrinsic_metadata()
            if intrinsic_metadata:
                logger.info(
                    f"Extracted intrinsic metadata for {domain_record.object_key}: "
                    f"{intrinsic_metadata}"
                )
                # Update the metadata on the Pydantic object before saving
                domain_record.metadata = (
                    domain_record.metadata or {}
                )  # Ensure metadata dict exists
                domain_record.metadata["intrinsic"] = intrinsic_metadata
            else:
                logger.warning(
                    f"No intrinsic metadata extracted for {domain_record.object_key}"
                )

            content = None  # Initialize content

            # 3. Generate and save thumbnail (safely)
            try:
                content = await processor.get_content()
                thumbnail_result = await processor.generate_thumbnail(content)
                if thumbnail_result:
                    thumbnail_bytes, thumbnail_mimetype = thumbnail_result
                    logger.info(
                        f"Generated thumbnail for {domain_record.object_key} with mimetype {thumbnail_mimetype}"
                    )
                else:
                    thumbnail_bytes = None
                    thumbnail_mimetype = None
            except Exception as thumb_exc:
                logger.warning(
                    f"Failed to generate thumbnail for {domain_record.object_key}: {thumb_exc}",
                    exc_info=True,  # Log traceback for debugging
                )
                thumbnail_bytes = None  # Ensure it's None on failure
                thumbnail_mimetype = None

            # 3b. Generate and save proxy (safely)
            if content:  # Only proceed if content was successfully retrieved
                try:
                    proxy_result = await processor.generate_proxy(content)
                    if proxy_result:
                        proxy_bytes, proxy_mimetype = proxy_result
                        logger.info(
                            f"Generated proxy for {domain_record.object_key} with mimetype {proxy_mimetype}"
                        )
                    else:
                        proxy_bytes = None
                        proxy_mimetype = None
                except Exception as proxy_exc:
                    logger.warning(
                        f"Failed to generate proxy for {domain_record.object_key}: {proxy_exc}",
                        exc_info=True,
                    )
                    proxy_bytes = None
                    proxy_mimetype = None
            else:
                logger.warning(
                    f"Skipping proxy generation for {domain_record.object_key} due to earlier content retrieval failure."
                )
                proxy_bytes = None
                proxy_mimetype = None

            # 4. Get or create the MediaObject record in the database
            db_media_object = repo.get_or_create(domain_record)

            if not db_media_object:
                logger.error(
                    f"Failed to commit MediaObject via repository for key: {domain_record.object_key}"
                )
                return False  # Indicate failure

            # 5. Store thumbnail if generated successfully
            if (
                thumbnail_bytes
                and thumbnail_mimetype
                and db_media_object
                and db_media_object.id
            ):
                try:
                    s3_storage.put_thumbnail(
                        str(db_media_object.id), thumbnail_bytes, thumbnail_mimetype
                    )
                    logger.info(
                        f"Stored thumbnail in S3 for {domain_record.object_key}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to store thumbnail in S3 for {domain_record.object_key}: {e}"
                    )
                    # S3 storage failure is critical
                    return False

            # 6. Store proxy if generated successfully
            if (
                proxy_bytes
                and proxy_mimetype
                and db_media_object
                and db_media_object.id
            ):
                try:
                    s3_storage.put_proxy(
                        str(db_media_object.id), proxy_bytes, proxy_mimetype
                    )
                    logger.info(f"Stored proxy in S3 for {domain_record.object_key}")
                except Exception as e:
                    logger.error(
                        f"Failed to store proxy in S3 for {domain_record.object_key}: {e}"
                    )
                    # S3 storage failure is critical
                    return False

            logger.info(
                f"Successfully processed and committed {domain_record.object_key}"
                + (" with" if intrinsic_metadata else " without")
                + " intrinsic metadata."
            )
            return True  # Indicate success

        except Exception as e:
            logger.exception(
                f"Error during intrinsic metadata extraction for {domain_record.object_key}: {e}"
            )
            # Continue without intrinsic metadata
            pass

        # 3. Use repository to commit/update the database object (fallback path)
        # Placeholder: Merge intrinsic metadata into the main metadata dictionary.
        # A dedicated DB field (e.g., JSONB) is the proper long-term solution.
        if domain_record.metadata is None:
            domain_record.metadata = {}

        # Only add intrinsic key if metadata was extracted
        if intrinsic_metadata:
            domain_record.metadata["intrinsic"] = intrinsic_metadata
        # Else: Commit the object with potentially only the original metadata

        # Commit the object (create or update)
        # Assuming repo.create handles potential updates or has get_or_create logic
        db_obj = repo.create(domain_record)

        if not db_obj:
            logger.error(
                f"Failed to commit MediaObject via repository for key: {domain_record.object_key}"
            )
            return False  # Indicate failure

        logger.info(
            f"Successfully processed and committed {domain_record.object_key}"
            + (" with" if intrinsic_metadata else " without")
            + " intrinsic metadata."
        )
        return True  # Indicate success

    except Exception as e:
        logger.exception(
            f"Error committing media object {domain_record.object_key} to DB: {e}"
        )
        return False  # Indicate failure
    finally:
        # Ensure proper cleanup of database session
        try:
            next(db_gen)
        except StopIteration:
            pass
