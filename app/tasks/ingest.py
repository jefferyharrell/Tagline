import logging
import os
from enum import Enum

import redis
from redis.exceptions import ConnectionError, LockNotOwnedError

from app.config import get_settings
from app.storage_provider import StorageProviderException, get_storage_provider

logger = logging.getLogger(__name__)


class IngestStatus(Enum):
    """Possible statuses for the ingest task."""

    STARTED = "started"
    COMPLETED = "completed"
    ALREADY_RUNNING = "already_running"
    FAILED_TO_ACQUIRE_LOCK = "failed_to_acquire_lock"
    FAILED = "failed"


async def ingest_orchestrator(redis_url: str | None = None) -> IngestStatus:
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
    # Use provided URL or default from environment
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
    # Use a reasonable timeout (e.g., 1 hour)
    lock_timeout = 3600
    lock = r.lock(lock_key, timeout=lock_timeout)

    try:
        if lock.acquire(blocking=False):
            logger.info("Acquired ingest lock. Starting ingest process.")
            try:
                # Get settings and storage provider instance
                settings = get_settings()
                storage_provider = get_storage_provider(settings)
                logger.info(
                    f"Using storage provider: {settings.STORAGE_PROVIDER.value}"
                )

                # Fetch media objects from the provider
                try:
                    media_objects = await storage_provider.list()
                    logger.info(
                        f"Fetched {len(media_objects)} media objects from storage."
                    )

                    from app.constants import SUPPORTED_MIMETYPES

                    filtered_media_objects = [
                        obj
                        for obj in media_objects
                        if (obj.metadata or {}).get("mimetype") in SUPPORTED_MIMETYPES
                    ]
                    num_filtered = len(media_objects) - len(filtered_media_objects)
                    if num_filtered:
                        logger.info(
                            f"Filtered out {num_filtered} unsupported media objects (by mimetype). Supported: {SUPPORTED_MIMETYPES}"
                        )
                    else:
                        logger.info("No unsupported media objects filtered out.")

                    for obj in filtered_media_objects:
                        logger.debug(f"Found: {obj}")
                    # Placeholder: Simulate work
                    import asyncio

                    await asyncio.sleep(5)  # Simulate time-consuming task
                    logger.info("Ingest process completed.")
                    return IngestStatus.COMPLETED
                except StorageProviderException as e:
                    logger.error(f"Storage provider error during ingest: {e}")
                    return IngestStatus.FAILED
                except Exception as e:
                    logger.exception(
                        f"Unexpected error during media object fetching: {e}"
                    )
                    return IngestStatus.FAILED

            finally:
                # Ensure the lock is always released
                try:
                    lock.release()
                    logger.info("Released ingest lock.")
                except LockNotOwnedError:
                    # This shouldn't happen if acquire was successful, but good to handle
                    logger.warning("Attempted to release a lock not owned.")
                except ConnectionError:
                    logger.error("Redis connection error while releasing lock.")
        else:
            logger.warning("Ingest process already running. Skipping.")
            return IngestStatus.ALREADY_RUNNING
    except ConnectionError:
        logger.error("Redis connection error while acquiring lock.")
        return IngestStatus.FAILED
    except Exception as e:
        logger.exception(f"Unexpected error in ingest orchestrator: {e}")
        return IngestStatus.FAILED
