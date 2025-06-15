"""
Redis event publishing utility for Tagline backend.

This module provides functionality to publish real-time ingest events
to Redis pub/sub channels for consumption by SSE endpoints.
"""

import os
from datetime import datetime, timezone
from typing import Literal, Optional

import redis
from pydantic import BaseModel

from app.schemas import MediaObject
from app.structlog_config import get_logger

logger = get_logger(__name__)

# Event types
EventType = Literal["queued", "started", "complete"]

# Redis channels
INGEST_EVENTS_CHANNEL = "ingest:events"


class IngestEvent(BaseModel):
    """Structure for ingest events published to Redis."""

    event_type: EventType
    timestamp: str
    media_object: MediaObject
    error: Optional[str] = None


class RedisEventPublisher:
    """Singleton Redis event publisher for ingest events."""

    _instance: Optional["RedisEventPublisher"] = None
    _redis_conn: Optional[redis.Redis] = None

    def __new__(cls) -> "RedisEventPublisher":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._redis_conn is None:
            self._connect()

    def _connect(self):
        """Initialize Redis connection."""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            self._redis_conn = redis.from_url(redis_url)
            # Test the connection
            self._redis_conn.ping()
            logger.info(
                "Redis event publisher connected",
                operation="redis_connect",
                redis_url=redis_url
            )
        except Exception as e:
            logger.error(
                "Failed to connect to Redis for event publishing",
                operation="redis_connect",
                error=str(e),
                error_type=type(e).__name__
            )
            self._redis_conn = None

    def _ensure_connected(self) -> bool:
        """Ensure Redis connection is active, reconnect if needed."""
        if self._redis_conn is None:
            self._connect()
            return self._redis_conn is not None

        try:
            self._redis_conn.ping()
            return True
        except redis.ConnectionError:
            logger.warning(
                "Redis connection lost, attempting to reconnect",
                operation="redis_reconnect",
                error_type="redis_connection_error"
            )
            self._connect()
            return self._redis_conn is not None

    def publish_event(
        self,
        event_type: EventType,
        media_object: MediaObject,
        error: Optional[str] = None,
    ) -> bool:
        """
        Publish an ingest event to Redis pub/sub.

        Args:
            event_type: Type of event (queued, started, complete)
            media_object: Full MediaObject data
            error: Optional error message for failed events

        Returns:
            bool: True if event was published successfully, False otherwise
        """
        if not self._ensure_connected():
            logger.error(
                "Cannot publish event: Redis connection failed",
                operation="publish_event",
                event_type=event_type,
                object_key=media_object.object_key,
                error_type="redis_connection_failed"
            )
            return False

        try:
            # Create event with current timestamp
            event = IngestEvent(
                event_type=event_type,
                timestamp=datetime.now(timezone.utc).isoformat(),
                media_object=media_object,
                error=error,
            )

            # Serialize to JSON
            event_json = event.model_dump_json()

            # Publish to Redis channel
            subscriber_count = self._redis_conn.publish(
                INGEST_EVENTS_CHANNEL, event_json
            )

            logger.info(
                "Published event to subscribers",
                operation="publish_event",
                event_type=event_type,
                object_key=media_object.object_key,
                subscriber_count=subscriber_count
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to publish event",
                operation="publish_event",
                event_type=event_type,
                object_key=media_object.object_key,
                error=str(e),
                error_type=type(e).__name__
            )
            return False


# Global publisher instance
_publisher = None


def get_event_publisher() -> RedisEventPublisher:
    """Get the global Redis event publisher instance."""
    global _publisher
    if _publisher is None:
        _publisher = RedisEventPublisher()
    return _publisher


def publish_queued_event(media_object: MediaObject) -> bool:
    """
    Publish a 'queued' event when a media object is queued for ingestion.

    Args:
        media_object: MediaObject that was queued

    Returns:
        bool: True if published successfully
    """
    publisher = get_event_publisher()
    return publisher.publish_event("queued", media_object)


def publish_started_event(media_object: MediaObject) -> bool:
    """
    Publish a 'started' event when ingestion begins for a media object.

    Args:
        media_object: MediaObject being processed

    Returns:
        bool: True if published successfully
    """
    publisher = get_event_publisher()
    return publisher.publish_event("started", media_object)


def publish_complete_event(
    media_object: MediaObject, error: Optional[str] = None
) -> bool:
    """
    Publish a 'complete' event when ingestion finishes for a media object.

    Args:
        media_object: MediaObject that finished processing
        error: Optional error message if ingestion failed

    Returns:
        bool: True if published successfully
    """
    publisher = get_event_publisher()
    return publisher.publish_event("complete", media_object, error)
