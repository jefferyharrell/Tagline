import logging
import os
from enum import Enum

import redis
from redis.exceptions import ConnectionError, LockNotOwnedError
from rq import Queue

from app.config import get_settings
from app.db.repositories.media_object import MediaObjectRepository
from app.storage_provider import StorageProviderException, get_storage_provider
from app.storage_types import MediaObject

logger = logging.getLogger(__name__)


class IngestStatus(Enum):
    """Possible statuses for the ingest task."""

    STARTED = "started"
    COMPLETED = "completed"
    ALREADY_RUNNING = "already_running"
    FAILED_TO_ACQUIRE_LOCK = "failed_to_acquire_lock"
    FAILED = "failed"


def ingest(media_object: MediaObject) -> bool:
    # Perform the actual processing for a single media object
    # This could involve downloading, analysis, thumbnail generation, etc.
    logger.info(f"Processing media object: {media_object.object_key}")
    logger.debug(f"  Metadata: {media_object.metadata}")
    logger.debug(f"  Last modified: {media_object.last_modified}")

    # Use repository to commit to database
    repo = MediaObjectRepository()
    db_obj = repo.create(media_object)

    if not db_obj:
        logger.error(
            f"Failed to commit MediaObject via repository for key: {media_object.object_key}"
        )
        # Decide if this should be a task failure
        return False  # Indicate failure

    # Return success to indicate the task completed
    return True


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
                    f"Fetching media objects from {storage_provider.provider_name}"  # Access as attribute
                )
                media_objects = storage_provider.list_media_objects()
                logger.info(f"Found {len(media_objects)} total media objects.")
            except StorageProviderException as e:
                logger.error(f"Storage provider error: {e}")
                return IngestStatus.FAILED
            except Exception as e:
                logger.exception(f"Unexpected error during object listing: {e}")
                return IngestStatus.FAILED

            # Filter out unsupported types (Example: only allow images for now)
            # This is basic filtering; more sophisticated logic might be needed
            from app.constants import SUPPORTED_MIMETYPES

            filtered_media_objects = [
                obj
                for obj in media_objects
                # Handle potential None metadata
                if (obj.metadata or {}).get("mimetype") in SUPPORTED_MIMETYPES
            ]
            unsupported_count = len(media_objects) - len(filtered_media_objects)
            if unsupported_count > 0:
                logger.info(
                    f"Filtered out {unsupported_count} unsupported media objects."
                )
            else:
                logger.info("No unsupported media objects filtered out.")

            # Queue individual ingest tasks for each media object
            redis_conn = redis.from_url(redis_url)
            queue = Queue(connection=redis_conn)

            # Instantiate repository
            repo = MediaObjectRepository()
            queued_count = 0

            for obj in filtered_media_objects:
                # Use repository to check existence
                exists = repo.get_by_object_key(obj.object_key)
                if exists:
                    logger.info(f"Skipping {obj.object_key}: already present in DB.")
                    continue

                # Queue the individual ingest task
                job = queue.enqueue(ingest, media_object=obj)
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
        # Ensure the lock is always released
        try:
            lock.release()
            logger.info("Released ingest lock.")
        except LockNotOwnedError:
            # This shouldn't happen if acquire was successful, but good to handle
            logger.warning("Attempted to release a lock not owned.")
        except ConnectionError:
            logger.error("Redis connection error while releasing lock.")
