import logging
import os
from enum import Enum

import redis
from redis.exceptions import ConnectionError, LockNotOwnedError
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
    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_port = int(os.environ.get("REDIS_PORT", 6379))
    redis_db = int(os.environ.get("REDIS_DB", 0))
    redis_password = os.environ.get("REDIS_PASSWORD", None)

    if redis_url:
        r = redis.from_url(redis_url)
    else:
        r = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
        )

    lock_key = "ingest_orchestrator_lock"
    lock_timeout = 3600
    lock = r.lock(lock_key, timeout=lock_timeout)

    try:
        if lock.acquire(blocking=False):
            logger.info("Acquired ingest lock. Starting ingest process.")
            try:
                settings = get_settings()
                storage_provider = get_storage_provider(settings)
                logger.info(
                    f"Fetching media objects from {storage_provider.provider_name}"
                )
                media_objects = storage_provider.list_media_objects()
                logger.info(f"Found {len(media_objects)} total media objects.")
            except StorageProviderException as e:
                logger.error(f"Storage provider error: {e}")
                return IngestStatus.FAILED
            except Exception as e:
                logger.exception(f"Unexpected error during object listing: {e}")
                return IngestStatus.FAILED

            filtered_media_objects = []
            unsupported_count = 0
            for obj in media_objects:
                mimetype = str((obj.metadata or {}).get("mimetype"))
                logger.debug(
                    f"Checking object {obj.object_key} with raw mimetype: {mimetype}"
                )
                if mimetype != "None" and is_mimetype_supported(mimetype):
                    filtered_media_objects.append(obj)
                    logger.debug(f"Object {obj.object_key} ({mimetype}) is SUPPORTED")
                else:
                    unsupported_count += 1
                    logger.debug(f"Object {obj.object_key} ({mimetype}) is UNSUPPORTED")

            if unsupported_count > 0:
                logger.info(
                    f"Filtered out {unsupported_count} unsupported media objects."
                )
            else:
                logger.info("No unsupported media objects filtered out.")

            redis_conn = redis.from_url(redis_url)
            ingest_queue = Queue('ingest', connection=redis_conn)
            repo = get_media_object_repository()
            queued_count = 0

            for obj in filtered_media_objects:
                exists = repo.get_by_object_key(obj.object_key)
                if exists:
                    logger.info(f"Skipping {obj.object_key}: already present in DB.")
                    continue
                job = ingest_queue.enqueue("app.tasks.ingest.ingest", media_object=obj)
                logger.debug(f"Queued ingest job {job.id} for {obj.object_key}")
                queued_count += 1

            logger.info(f"Queued {queued_count} new media objects for processing")
            logger.info("Ingest process completed.")
            return IngestStatus.COMPLETED
        else:
            logger.warning("Ingest process already running. Skipping.")
            return IngestStatus.ALREADY_RUNNING
    except ConnectionError:
        logger.error("Redis connection error while acquiring lock.")
        return IngestStatus.FAILED
    except Exception as e:
        logger.exception(f"Unexpected error in ingest orchestrator: {e}")
        return IngestStatus.FAILED
    finally:
        try:
            lock.release()
            logger.info("Released ingest lock.")
        except LockNotOwnedError:
            logger.warning("Attempted to release a lock not owned.")
        except ConnectionError:
            logger.error("Redis connection error while releasing lock.")
