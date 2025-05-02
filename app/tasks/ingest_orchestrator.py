import logging
from enum import Enum

import redis
from redis.exceptions import ConnectionError
from rq import Queue

from app.config import get_settings
from app.dependencies import get_media_object_repository
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
    # Redis connection will be handled by redis_conn below; remove unused variable assignment.

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
            return IngestStatus.FAILED
        except Exception as e:
            logger.exception(f"Unexpected error during object listing: {e}")
            return IngestStatus.FAILED

        unsupported_count = 0
        queued_count = 0
        total_count = 0
        job_ids = []
        redis_conn = redis.from_url(redis_url)
        ingest_queue = Queue("ingest", connection=redis_conn)
        repo = get_media_object_repository()

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
            job = ingest_queue.enqueue("app.tasks.ingest.ingest", media_object=obj)
            logger.debug(f"Queued ingest job {job.id} for {obj.object_key}")
            job_ids.append(job.id)
            queued_count += 1

        logger.info(f"Found {total_count} total media objects.")
        if unsupported_count > 0:
            logger.info(f"Filtered out {unsupported_count} unsupported media objects.")
        else:
            logger.info("No unsupported media objects filtered out.")
        logger.info(f"Queued {queued_count} new media objects for processing")

        # Wait for all ingest jobs to finish
        import time

        from rq.job import Job

        poll_interval = 5  # seconds
        logger.info(f"Waiting for {len(job_ids)} ingest jobs to finish...")
        while job_ids:
            remaining = []
            for jid in job_ids:
                try:
                    j = Job.fetch(jid, connection=redis_conn)
                    if j.get_status() not in (
                        "finished",
                        "failed",
                        "stopped",
                    ):  # still running
                        remaining.append(jid)
                except Exception:
                    # If job can't be fetched, treat as finished
                    continue
            if not remaining:
                break
            logger.info(f"Still waiting for {len(remaining)} jobs...")
            time.sleep(poll_interval)
            job_ids = remaining
        logger.info("All ingest jobs finished. Ingest process completed.")
        return IngestStatus.COMPLETED
    except ConnectionError:
        logger.error("Redis connection error during ingest orchestrator.")
        return IngestStatus.FAILED
    except Exception as e:
        logger.exception(f"Unexpected error in ingest orchestrator: {e}")
        return IngestStatus.FAILED
