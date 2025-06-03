import logging

# Import necessary components for media processing
from app.config import get_settings
from app.db.database import get_db
from app.db.repositories.media_object import MediaObjectRepository
from app.models import IngestionStatus

# Import processor modules to trigger registration via decorators
# The noqa comment prevents linters from flagging unused import, which is needed here.
from app.media_processing import heicprocessor  # noqa: F401
from app.media_processing import jpegprocessor  # noqa: F401
from app.media_processing.factory import get_processor
from app.s3_binary_storage import S3BinaryStorage, S3Config
from app.schemas import StoredMediaObject

logger = logging.getLogger(__name__)


async def ingest(object_key: str) -> bool:
    """Processes a single media object: extracts metadata and generates thumbnails/proxies.
    
    Args:
        object_key: The object key of the MediaObject to process
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Starting ingestion for object_key: {object_key}")
    intrinsic_metadata = {}

    # Create a database session for this task
    db_gen = get_db()
    db = next(db_gen)
    repo = MediaObjectRepository(db)

    try:
        
        # Update status to processing
        if not repo.update_ingestion_status(object_key, IngestionStatus.PROCESSING.value):
            logger.error(f"MediaObject not found for key: {object_key}")
            return False

        # Get the MediaObject from database
        media_obj = repo.get_by_object_key(object_key)
        if not media_obj:
            logger.error(f"Failed to retrieve MediaObject for key: {object_key}")
            return False

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
            repo.update_ingestion_status(object_key, IngestionStatus.FAILED.value)
            return False

        config = S3Config(
            endpoint_url=settings.S3_ENDPOINT_URL,  # type: ignore[arg-type]
            access_key_id=settings.S3_ACCESS_KEY_ID,  # type: ignore[arg-type]
            secret_access_key=settings.S3_SECRET_ACCESS_KEY,  # type: ignore[arg-type]
            bucket_name=settings.S3_BUCKET_NAME,  # type: ignore[arg-type]
            region=settings.S3_REGION,
        )
        s3_storage = S3BinaryStorage(config)

        # Create a StoredMediaObject for processor compatibility
        stored_media_obj = StoredMediaObject(
            object_key=object_key,
            last_modified=media_obj.file_last_modified.isoformat() if media_obj.file_last_modified else None,
            metadata={
                "size": media_obj.file_size,
                "mimetype": media_obj.file_mimetype,
            }
        )

        try:
            # 1. Try to get the appropriate processor
            processor = get_processor(stored_media_obj)

            # 2. Extract intrinsic metadata if processor found
            intrinsic_metadata = await processor.extract_intrinsic_metadata()
            if intrinsic_metadata:
                logger.info(
                    f"Extracted intrinsic metadata for {object_key}: "
                    f"{intrinsic_metadata}"
                )
            else:
                logger.warning(
                    f"No intrinsic metadata extracted for {object_key}"
                )

            content = None  # Initialize content

            # 3. Generate and save thumbnail (safely)
            try:
                content = await processor.get_content()
                thumbnail_result = await processor.generate_thumbnail(content)
                if thumbnail_result:
                    thumbnail_bytes, thumbnail_mimetype = thumbnail_result
                    logger.info(
                        f"Generated thumbnail for {object_key} with mimetype {thumbnail_mimetype}"
                    )
                else:
                    thumbnail_bytes = None
                    thumbnail_mimetype = None
            except Exception as thumb_exc:
                logger.warning(
                    f"Failed to generate thumbnail for {object_key}: {thumb_exc}",
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
                            f"Generated proxy for {object_key} with mimetype {proxy_mimetype}"
                        )
                    else:
                        proxy_bytes = None
                        proxy_mimetype = None
                except Exception as proxy_exc:
                    logger.warning(
                        f"Failed to generate proxy for {object_key}: {proxy_exc}",
                        exc_info=True,
                    )
                    proxy_bytes = None
                    proxy_mimetype = None
            else:
                logger.warning(
                    f"Skipping proxy generation for {object_key} due to earlier content retrieval failure."
                )
                proxy_bytes = None
                proxy_mimetype = None

            # 4. Store thumbnail if generated successfully
            if thumbnail_bytes and thumbnail_mimetype:
                try:
                    # Store in S3 using object_key as the identifier
                    s3_key = s3_storage.put_thumbnail(
                        object_key, thumbnail_bytes, thumbnail_mimetype
                    )
                    # Register S3 key in database
                    repo.register_thumbnail(
                        object_key,
                        s3_key,
                        thumbnail_mimetype,
                        len(thumbnail_bytes),
                    )
                    logger.info(
                        f"Stored thumbnail in S3 for {object_key}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to store thumbnail in S3 for {object_key}: {e}"
                    )
                    repo.update_ingestion_status(object_key, IngestionStatus.FAILED.value)
                    return False

            # 5. Store proxy if generated successfully
            if proxy_bytes and proxy_mimetype:
                try:
                    # Store in S3 using object_key as the identifier
                    s3_key = s3_storage.put_proxy(
                        object_key, proxy_bytes, proxy_mimetype
                    )
                    # Register S3 key in database
                    repo.register_proxy(
                        object_key, s3_key, proxy_mimetype, len(proxy_bytes)
                    )
                    logger.info(f"Stored proxy in S3 for {object_key}")
                except Exception as e:
                    logger.error(
                        f"Failed to store proxy in S3 for {object_key}: {e}"
                    )
                    repo.update_ingestion_status(object_key, IngestionStatus.FAILED.value)
                    return False

            # 6. Update MediaObject with extracted metadata
            metadata_to_update = {}
            if intrinsic_metadata:
                metadata_to_update["intrinsic"] = intrinsic_metadata
            
            if metadata_to_update:
                repo.update_after_ingestion(object_key, metadata_to_update)
            else:
                # Just mark as completed
                repo.update_ingestion_status(object_key, IngestionStatus.COMPLETED.value)

            logger.info(
                f"Successfully processed {object_key}"
                + (" with" if intrinsic_metadata else " without")
                + " intrinsic metadata."
            )
            return True  # Indicate success

        except Exception as e:
            logger.exception(
                f"Error during processing for {object_key}: {e}"
            )
            repo.update_ingestion_status(object_key, IngestionStatus.FAILED.value)
            return False

    except Exception as e:
        logger.exception(
            f"Error processing media object {object_key}: {e}"
        )
        try:
            repo.update_ingestion_status(object_key, IngestionStatus.FAILED.value)
        except Exception:
            pass
        return False
    finally:
        # Ensure proper cleanup of database session
        try:
            next(db_gen)
        except StopIteration:
            pass
