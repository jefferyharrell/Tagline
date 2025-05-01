import logging
import os
import time
from enum import Enum

import redis
from redis.exceptions import ConnectionError, LockNotOwnedError

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


class IngestStatus(Enum):
    """Possible statuses for the ingest task."""

    STARTED = "started"
    COMPLETED = "completed"
    ALREADY_RUNNING = "already_running"
    FAILED_TO_ACQUIRE_LOCK = "failed_to_acquire_lock"
    FAILED = "failed"


def ingest_orchestrator(redis_url: str | None = None) -> IngestStatus:
    """
    Orchestrator for the ingest process. Acquires the ingest lock, fetches all media objects from the storage provider (stub), and releases the lock.
    """
    redis_url = redis_url or os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        r = redis.from_url(redis_url)
        r.ping()
    except ConnectionError as e:
        logger.error(f"Orchestrator could not connect to Redis: {e}")
        return IngestStatus.FAILED_TO_ACQUIRE_LOCK

    lock_key = "ingest:lock"
    lock = r.lock(lock_key, timeout=10800, blocking_timeout=0)
    if not lock.acquire():
        logger.info("Ingest orchestrator already running (lock busy). Exiting.")
        return IngestStatus.ALREADY_RUNNING

    try:
        logger.info(
            "Ingest orchestrator started (lock acquired). Fetching media objects..."
        )
        # --- STUB: Fetch media objects from storage provider ---
        # Replace this with actual storage provider integration
        media_objects = ["media1", "media2", "media3"]
        logger.info(f"Fetched {len(media_objects)} media objects: {media_objects}")
        # ------------------------------------------------------
        logger.info("Ingest orchestrator completed.")
        return IngestStatus.COMPLETED
    except Exception as e:
        logger.error(f"Error during ingest orchestrator: {e}", exc_info=True)
        return IngestStatus.FAILED
    finally:
        try:
            lock.release()
            logger.info("Ingest orchestrator lock released.")
        except LockNotOwnedError:
            logger.warning(
                "Could not release ingest orchestrator lock (possibly expired or not owned)."
            )
        except Exception as e:
            logger.error(
                f"Error releasing ingest orchestrator lock: {e}", exc_info=True
            )
