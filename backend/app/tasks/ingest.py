import gc
import logging
import time

# Import only lightweight dependencies at startup
from app.schemas import StoredMediaObject

# Heavy dependencies imported lazily:
# - S3BinaryStorage/boto3 (AWS SDK ~100-200MB)
# - SQLAlchemy models and repositories (~50-100MB)
# - Media processors with pillow-heif (~100-200MB)
# - Redis events (~10-50MB)


# Module-level logger - will be replaced with JSON logger in the function
logger = logging.getLogger(__name__)


async def ingest(object_key: str) -> bool:
    """Processes a single media object: extracts metadata and generates thumbnails/proxies.

    Args:
        object_key: The object key of the MediaObject to process

    Returns:
        True if successful, False otherwise
    """
    # Configure structlog for this worker process if not already done
    global logger
    if not hasattr(logging.getLogger(), "_structlog_configured"):
        from app.config import get_settings
        from app.structlog_config import configure_structlog

        settings = get_settings()
        configure_structlog(
            service_name="tagline-ingest-worker", log_format=settings.LOG_FORMAT
        )
        logging.getLogger()._structlog_configured = True

    # Create a fresh logger instance for this job to avoid context pollution
    from app.structlog_config import get_job_logger

    # Start timing the entire job
    job_start_time = time.time()
    job_id = f"ingest-{int(job_start_time)}-{object_key.replace('/', '-')}"

    # Create logger with job context
    job_logger = get_job_logger(
        __name__, job_id=job_id, file_path=object_key, operation="ingest"
    )

    job_logger.info("Starting ingestion job", operation="job_start")
    intrinsic_metadata = {}

    # Lazy import heavy database dependencies
    from app.db.database import get_db
    from app.db.repositories.media_object import MediaObjectRepository
    from app.models import IngestionStatus

    # Create a database session for this task
    db_gen = get_db()
    db = next(db_gen)
    repo = MediaObjectRepository(db)

    try:

        # Update status to processing
        db_start = time.time()
        if not repo.update_ingestion_status(
            object_key, IngestionStatus.PROCESSING.value
        ):
            job_logger.error(
                "MediaObject not found",
                operation="db_update_status",
                status="not_found",
            )
            return False
        job_logger.info(
            "Updated ingestion status to processing",
            operation="db_update_status",
            duration_ms=(time.time() - db_start) * 1000,
        )

        # Get the MediaObject from database
        db_start = time.time()
        media_obj = repo.get_by_object_key(object_key)
        if not media_obj:
            job_logger.error(
                "Failed to retrieve MediaObject",
                operation="db_get_object",
                status="not_found",
            )
            return False
        job_logger.info(
            "Retrieved MediaObject from database",
            operation="db_get_object",
            duration_ms=(time.time() - db_start) * 1000,
            file_size=media_obj.file_size,
            file_mimetype=media_obj.file_mimetype,
        )

        # Lazy import Redis events
        from app.redis_events import publish_complete_event, publish_started_event

        # Publish started event
        try:
            event_start = time.time()
            media_obj_pydantic = media_obj.to_pydantic()
            publish_started_event(media_obj_pydantic)
            job_logger.info(
                "Published started event",
                operation="redis_publish",
                event_type="started",
                duration_ms=(time.time() - event_start) * 1000,
            )
        except Exception as e:
            job_logger.warning(
                "Failed to publish started event",
                operation="redis_publish",
                event_type="started",
                error=str(e),
            )

        # Lazy import S3 storage (boto3 is memory-heavy)
        from app.s3_binary_storage import S3BinaryStorage, S3Config

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
            job_logger.error(
                "S3 configuration is incomplete",
                operation="s3_init",
                status="config_error",
                missing_configs=[
                    k
                    for k in [
                        "S3_ENDPOINT_URL",
                        "S3_ACCESS_KEY_ID",
                        "S3_SECRET_ACCESS_KEY",
                        "S3_BUCKET_NAME",
                    ]
                    if not getattr(settings, k, None)
                ],
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
            last_modified=(
                media_obj.file_last_modified.isoformat()
                if media_obj.file_last_modified
                else None
            ),
            metadata={
                "size": media_obj.file_size,
                "mimetype": media_obj.file_mimetype,
            },
        )

        processor = None
        content = None
        thumbnail_bytes = None
        proxy_bytes = None
        content_hash = None

        try:
            # Lazy import media processor factory
            from app.media_processing.factory import get_processor

            # 1. Try to get the appropriate processor
            processor = get_processor(stored_media_obj)

            # 2. Extract intrinsic metadata if processor found
            metadata_start = time.time()
            intrinsic_metadata = await processor.extract_intrinsic_metadata()
            if intrinsic_metadata:
                job_logger.info(
                    "Extracted intrinsic metadata",
                    operation="extract_metadata",
                    duration_ms=(time.time() - metadata_start) * 1000,
                    metadata_keys=list(intrinsic_metadata.keys()),
                )
            else:
                job_logger.warning(
                    "No intrinsic metadata extracted",
                    operation="extract_metadata",
                    duration_ms=(time.time() - metadata_start) * 1000,
                )

            content = None  # Initialize content

            # 3. Generate and save thumbnail (safely)
            try:
                content_start = time.time()
                content = await processor.get_content()
                job_logger.info(
                    "Retrieved content from storage provider",
                    operation="get_content",
                    duration_ms=(time.time() - content_start) * 1000,
                )

                # Compute content hash for move detection
                if content:
                    hash_start = time.time()
                    try:
                        from app.utils.hashing import compute_content_hash_sync
                        content_hash = compute_content_hash_sync(content)
                        if content_hash:
                            job_logger.info(
                                "Computed content hash",
                                operation="compute_hash",
                                duration_ms=(time.time() - hash_start) * 1000,
                                content_hash=content_hash,
                                content_size=len(content)
                            )
                        else:
                            job_logger.warning(
                                "Failed to compute content hash",
                                operation="compute_hash",
                                duration_ms=(time.time() - hash_start) * 1000,
                            )
                    except Exception as hash_exc:
                        job_logger.error(
                            "Error computing content hash",
                            operation="compute_hash",
                            duration_ms=(time.time() - hash_start) * 1000,
                            error=str(hash_exc),
                            error_type=type(hash_exc).__name__,
                        )

                thumb_start = time.time()
                thumbnail_result = await processor.generate_thumbnail(content)
                if thumbnail_result:
                    thumbnail_bytes, thumbnail_mimetype = thumbnail_result
                    job_logger.info(
                        "Generated thumbnail",
                        operation="thumbnail_generation",
                        duration_ms=(time.time() - thumb_start) * 1000,
                        thumbnail_size=len(thumbnail_bytes),
                        thumbnail_mimetype=thumbnail_mimetype,
                    )
                else:
                    thumbnail_bytes = None
                    thumbnail_mimetype = None
                    job_logger.warning(
                        "No thumbnail generated",
                        operation="thumbnail_generation",
                        duration_ms=(time.time() - thumb_start) * 1000,
                    )
            except Exception as thumb_exc:
                job_logger.error(
                    "Failed to generate thumbnail",
                    operation="thumbnail_generation",
                    error=str(thumb_exc),
                    error_type=type(thumb_exc).__name__,
                )
                thumbnail_bytes = None  # Ensure it's None on failure
                thumbnail_mimetype = None

            # 3b. Generate and save proxy (safely)
            if content:  # Only proceed if content was successfully retrieved
                try:
                    proxy_start = time.time()
                    proxy_result = await processor.generate_proxy(content)
                    if proxy_result:
                        proxy_bytes, proxy_mimetype = proxy_result
                        job_logger.info(
                            "Generated proxy",
                            operation="proxy_generation",
                            duration_ms=(time.time() - proxy_start) * 1000,
                            proxy_size=len(proxy_bytes),
                            proxy_mimetype=proxy_mimetype,
                        )
                    else:
                        proxy_bytes = None
                        proxy_mimetype = None
                        job_logger.warning(
                            "No proxy generated",
                            operation="proxy_generation",
                            duration_ms=(time.time() - proxy_start) * 1000,
                        )
                except Exception as proxy_exc:
                    job_logger.error(
                        "Failed to generate proxy",
                        operation="proxy_generation",
                        error=str(proxy_exc),
                        error_type=type(proxy_exc).__name__,
                    )
                    proxy_bytes = None
                    proxy_mimetype = None
            else:
                job_logger.warning(
                    "Skipping proxy generation due to missing content",
                    operation="proxy_generation",
                    status="skipped",
                )
                proxy_bytes = None
                proxy_mimetype = None

            # 4. Store thumbnail if generated successfully
            if thumbnail_bytes and thumbnail_mimetype:
                try:
                    # Store in S3 using object_key as the identifier
                    s3_start = time.time()
                    s3_key = s3_storage.put_thumbnail(
                        object_key, thumbnail_bytes, thumbnail_mimetype
                    )
                    s3_duration = (time.time() - s3_start) * 1000

                    # Register S3 key in database
                    db_start = time.time()
                    repo.register_thumbnail(
                        object_key,
                        s3_key,
                        thumbnail_mimetype,
                        len(thumbnail_bytes),
                    )
                    db_duration = (time.time() - db_start) * 1000

                    job_logger.info(
                        "Stored thumbnail in S3 and registered in database",
                        operation="s3_store_thumbnail",
                        s3_duration_ms=s3_duration,
                        db_duration_ms=db_duration,
                        s3_key=s3_key,
                    )
                except Exception as e:
                    job_logger.error(
                        "Failed to store thumbnail",
                        operation="s3_store_thumbnail",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    repo.update_ingestion_status(
                        object_key, IngestionStatus.FAILED.value
                    )
                    return False

            # 5. Store proxy if generated successfully
            if proxy_bytes and proxy_mimetype:
                try:
                    # Store in S3 using object_key as the identifier
                    s3_start = time.time()
                    s3_key = s3_storage.put_proxy(
                        object_key, proxy_bytes, proxy_mimetype
                    )
                    s3_duration = (time.time() - s3_start) * 1000

                    # Register S3 key in database
                    db_start = time.time()
                    repo.register_proxy(
                        object_key, s3_key, proxy_mimetype, len(proxy_bytes)
                    )
                    db_duration = (time.time() - db_start) * 1000

                    job_logger.info(
                        "Stored proxy in S3 and registered in database",
                        operation="s3_store_proxy",
                        s3_duration_ms=s3_duration,
                        db_duration_ms=db_duration,
                        s3_key=s3_key,
                    )
                except Exception as e:
                    job_logger.error(
                        "Failed to store proxy",
                        operation="s3_store_proxy",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    repo.update_ingestion_status(
                        object_key, IngestionStatus.FAILED.value
                    )
                    return False

            # 6. Update MediaObject with extracted metadata
            metadata_to_update = {}
            if intrinsic_metadata:
                metadata_to_update["intrinsic"] = intrinsic_metadata

            if metadata_to_update:
                repo.update_after_ingestion(object_key, metadata_to_update)
            else:
                # Just mark as completed
                repo.update_ingestion_status(
                    object_key, IngestionStatus.COMPLETED.value
                )
            
            # 7. Update content hash if computed successfully
            if content_hash:
                try:
                    hash_update_start = time.time()
                    repo.update_content_hash(object_key, content_hash)
                    job_logger.info(
                        "Content hash stored in database",
                        operation="update_content_hash",
                        duration_ms=(time.time() - hash_update_start) * 1000,
                        content_hash=content_hash
                    )
                except Exception as e:
                    job_logger.error(
                        "Failed to update content hash in database",
                        operation="update_content_hash",
                        error=str(e),
                        error_type=type(e).__name__,
                        content_hash=content_hash
                    )

            # Calculate total job duration
            total_duration = (time.time() - job_start_time) * 1000

            job_logger.info(
                "Successfully completed ingestion job",
                operation="job_complete",
                total_duration_ms=total_duration,
                has_intrinsic_metadata=bool(intrinsic_metadata),
                has_thumbnail=bool(thumbnail_bytes),
                has_proxy=bool(proxy_bytes),
            )

            # Publish successful completion event
            try:
                event_start = time.time()
                # Get updated MediaObject to include latest data
                updated_media_obj = repo.get_by_object_key(object_key)
                if updated_media_obj:
                    media_obj_pydantic = updated_media_obj.to_pydantic()
                    publish_complete_event(media_obj_pydantic)
                    job_logger.info(
                        "Published complete event",
                        operation="redis_publish",
                        event_type="complete",
                        duration_ms=(time.time() - event_start) * 1000,
                    )
            except Exception as e:
                job_logger.warning(
                    "Failed to publish complete event",
                    operation="redis_publish",
                    event_type="complete",
                    error=str(e),
                )

            # Force garbage collection to free memory immediately
            gc.collect()

            return True  # Indicate success

        except Exception as e:
            total_duration = (time.time() - job_start_time) * 1000
            job_logger.exception(
                "Error during processing",
                operation="job_failed",
                total_duration_ms=total_duration,
                error=str(e),
                error_type=type(e).__name__,
            )
            repo.update_ingestion_status(object_key, IngestionStatus.FAILED.value)

            # Publish failed completion event
            try:
                event_start = time.time()
                failed_media_obj = repo.get_by_object_key(object_key)
                if failed_media_obj:
                    media_obj_pydantic = failed_media_obj.to_pydantic()
                    publish_complete_event(media_obj_pydantic, error=str(e))
                    job_logger.info(
                        "Published failed complete event",
                        operation="redis_publish",
                        event_type="complete_failed",
                        duration_ms=(time.time() - event_start) * 1000,
                    )
            except Exception as pub_error:
                job_logger.warning(
                    "Failed to publish failed complete event",
                    operation="redis_publish",
                    event_type="complete_failed",
                    error=str(pub_error),
                )

            # Force garbage collection on error to free any allocated memory
            gc.collect()

            return False

    except Exception as e:
        total_duration = (time.time() - job_start_time) * 1000
        job_logger.exception(
            "Critical error processing media object",
            operation="job_critical_failure",
            total_duration_ms=total_duration,
            error=str(e),
            error_type=type(e).__name__,
        )
        try:
            repo.update_ingestion_status(object_key, IngestionStatus.FAILED.value)

            # Publish failed completion event
            try:
                from app.redis_events import publish_complete_event

                failed_media_obj = repo.get_by_object_key(object_key)
                if failed_media_obj:
                    media_obj_pydantic = failed_media_obj.to_pydantic()
                    publish_complete_event(media_obj_pydantic, error=str(e))
                    job_logger.info(
                        "Published critical failure event",
                        operation="redis_publish",
                        event_type="complete_critical_failed",
                    )
            except Exception as pub_error:
                job_logger.warning(
                    "Failed to publish critical failure event",
                    operation="redis_publish",
                    event_type="complete_critical_failed",
                    error=str(pub_error),
                )

        except Exception:
            pass

        # Force garbage collection on outer exception to free any allocated memory
        gc.collect()
        return False
    finally:
        # Comprehensive memory cleanup - always runs regardless of success/failure
        try:
            # Clear processor content cache
            if processor is not None:
                processor.clear_content_cache()

            # Explicitly delete large variables if they exist
            if "content" in locals() and content is not None:
                del content
            if "thumbnail_bytes" in locals() and thumbnail_bytes is not None:
                del thumbnail_bytes
            if "proxy_bytes" in locals() and proxy_bytes is not None:
                del proxy_bytes
            if "processor" in locals() and processor is not None:
                del processor

            # Force garbage collection
            gc.collect()
            job_logger.info("Completed memory cleanup", operation="memory_cleanup")
        except Exception as cleanup_error:
            job_logger.warning(
                f"Error during memory cleanup for {object_key}: {cleanup_error}"
            )

        # Ensure proper cleanup of database session
        try:
            next(db_gen)
        except StopIteration:
            pass
