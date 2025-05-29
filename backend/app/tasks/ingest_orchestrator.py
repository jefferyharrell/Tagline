import logging
from enum import Enum

import redis
from redis.exceptions import ConnectionError
from rq import Queue, get_current_job
from rq.exceptions import NoSuchJobError
from rq.job import Job

from app.config import get_settings
from app.db.database import get_db
from app.db.repositories.media_object import MediaObjectRepository
from app.media_processing.factory import is_mimetype_supported
from app.storage_provider import StorageProviderException, get_storage_provider

logger = logging.getLogger(__name__)


class IngestStatus(Enum):
    """Possible statuses for the ingest task."""

    STARTED = "started"
    COMPLETED = "completed"
    ALREADY_RUNNING = "already_running"
    FAILED_TO_ACQUIRE_LOCK = "failed_to_acquire_lock"
    FAILED = "failed"


async def ingest_orchestrator(
    redis_url: str | None = None,
) -> IngestStatus:
    """Orchestrates the media ingest process.

    1. Attempts to acquire a Redis lock to prevent concurrent runs.
    2. If successful, fetches media objects from the configured storage provider.
    3. Logs the results.
    4. Releases the lock.

    Args:
        redis_url: Optional Redis connection URL for the lock.

    Returns:
        IngestStatus indicating the outcome.
    """
    orchestrator_job = get_current_job()
    if not orchestrator_job:
        logger.error("Orchestrator running outside of RQ worker context?")
        return IngestStatus.FAILED

    logger.info(f"Ingest orchestrator started with job ID: {orchestrator_job.id}")
    try:
        logger.info("Starting ingest process.")
        try:
            settings = get_settings()
            storage_provider = get_storage_provider(settings)
            logger.info(f"Fetching media objects from {storage_provider.provider_name}")
            # Use the new generator for efficient iteration
            logger.info(
                f"Iterating media objects from {storage_provider.provider_name}"
            )
            media_objects_iter = storage_provider.all_media_objects()
            # We'll count as we go
            total_count = 0
        except StorageProviderException as e:
            logger.error(f"Storage provider error: {e}")
            orchestrator_job.meta["current_stage"] = "error_fetching"
            orchestrator_job.meta["error_message"] = str(e)
            orchestrator_job.save_meta()
            return IngestStatus.FAILED
        except Exception as e:
            logger.exception(f"Unexpected error during object listing: {e}")
            orchestrator_job.meta["current_stage"] = "error_unknown"
            orchestrator_job.meta["error_message"] = str(e)
            orchestrator_job.save_meta()
            return IngestStatus.FAILED

        unsupported_count = 0
        queued_count = 0
        job_ids = []

        logger.info(
            f"Connecting to Redis at {redis_url} for orchestrator job management."
        )
        redis_conn = redis.from_url(redis_url)
        redis_conn.ping()  # Test connection
        ingest_queue = Queue("ingest", connection=redis_conn)

        # Create a database session for this orchestrator task
        db_gen = get_db()
        db = next(db_gen)
        try:
            repo = MediaObjectRepository(db)

            # Initialize metadata
            orchestrator_job.meta["total_items"] = 0
            orchestrator_job.meta["processed_items"] = 0
            orchestrator_job.meta["current_stage"] = "fetching_items"
            orchestrator_job.save_meta()

            for obj in media_objects_iter:
                total_count += 1
                mimetype = str((obj.metadata or {}).get("mimetype"))
                logger.debug(
                    f"Checking object {obj.object_key} with raw mimetype: {mimetype}"
                )
                if mimetype == "None" or not is_mimetype_supported(mimetype):
                    unsupported_count += 1
                    logger.debug(f"Object {obj.object_key} ({mimetype}) is UNSUPPORTED")
                    continue
                logger.debug(f"Object {obj.object_key} ({mimetype}) is SUPPORTED")
                exists = repo.get_by_object_key(obj.object_key)
                if exists:
                    logger.info(f"Skipping {obj.object_key}: already present in DB.")
                    continue
                orchestrator_job.meta["total_items"] = total_count
                orchestrator_job.meta["current_stage"] = "enqueueing_items"
                orchestrator_job.save_meta()
                ingest_job = ingest_queue.enqueue(
                    "app.tasks.ingest.ingest", stored_media_object=obj
                )
                logger.debug(f"Queued ingest job {ingest_job.id} for {obj.object_key}")
                job_ids.append(ingest_job.id)
                queued_count += 1

            logger.info(f"Found {total_count} total media objects.")
            if unsupported_count > 0:
                logger.info(
                    f"Filtered out {unsupported_count} unsupported media objects."
                )
            else:
                logger.info("No unsupported media objects filtered out.")
            logger.info(f"Queued {queued_count} new media objects for processing")

            logger.info(f"Finished enqueueing {queued_count} items for ingestion.")

            # Set stage to indicate waiting for jobs to finish
            orchestrator_job.meta["current_stage"] = "waiting_for_ingest_jobs"
            orchestrator_job.save_meta()

            # Wait for all ingest jobs to finish
            import time

            poll_interval = 1  # seconds
            logger.info(f"Waiting for {len(job_ids)} ingest jobs to finish...")
            completed_count = 0
            total_jobs = len(job_ids)

            while job_ids:
                remaining = []
                newly_completed = 0

                for job_id in job_ids:
                    try:
                        job = Job.fetch(job_id, connection=redis_conn)
                        if job.is_finished:
                            logger.debug(f"Job {job_id} finished.")
                            newly_completed += 1
                        else:
                            remaining.append(job_id)
                    except NoSuchJobError:
                        logger.warning(f"Job {job_id} not found.")
                        # Count as completed since we can't track it anymore
                        newly_completed += 1
                    except Exception as e:
                        logger.exception(f"Error checking job {job_id}: {e}")
                        remaining.append(job_id)

                # Update completion count and metadata
                if newly_completed > 0:
                    completed_count += newly_completed
                    # Update the metadata to show progress
                    orchestrator_job.meta["processed_items"] = completed_count
                    orchestrator_job.meta["current_stage"] = (
                        "monitoring_ingest_completion"
                    )
                    orchestrator_job.meta["progress_percent"] = int(
                        (completed_count / total_jobs) * 100
                    )
                    orchestrator_job.save_meta()
                    logger.info(
                        f"Progress: {completed_count}/{total_jobs} items processed ({orchestrator_job.meta['progress_percent']}%)"
                    )

                time.sleep(poll_interval)
                job_ids = remaining
                logger.info(f"Still waiting for {len(remaining)} jobs...")

            logger.info("All ingest jobs finished. Ingest process completed.")
            # The final status 'completed' is handled by RQ when the task returns IngestStatus.COMPLETED
            orchestrator_job.meta["processed_items"] = (
                total_count  # Final update to total count
            )
            orchestrator_job.meta["current_stage"] = (
                IngestStatus.COMPLETED.value
            )  # Use the enum value for the final stage
            orchestrator_job.save_meta()
            return IngestStatus.COMPLETED
        finally:
            # Ensure proper cleanup of database session
            try:
                next(db_gen)
            except StopIteration:
                pass
    except ConnectionError:
        logger.error("Redis connection error during ingest orchestrator.")
        orchestrator_job.meta["current_stage"] = "error_redis"
        orchestrator_job.meta["error_message"] = "Could not connect to Redis"
        orchestrator_job.save_meta()
        return IngestStatus.FAILED
    except Exception as e:
        logger.exception(f"Unexpected error in ingest orchestrator: {e}")
        orchestrator_job.meta["current_stage"] = "error_unknown"
        orchestrator_job.meta["error_message"] = str(e)
        orchestrator_job.save_meta()
        return IngestStatus.FAILED
    finally:
        logger.info(f"Ingest orchestrator finished for job ID: {orchestrator_job.id}")
