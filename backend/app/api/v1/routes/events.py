"""
Server-Sent Events routes for real-time updates.

This module provides SSE endpoints for:
- Real-time ingest progress updates via Redis pub/sub
- Media object status notifications (queued, started, complete)
"""

import asyncio
import json
import os
from typing import AsyncGenerator, Optional

import redis
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app import auth_schemas as schemas
from app.auth_utils import get_current_user
from app.redis_events import INGEST_EVENTS_CHANNEL
from app.structlog_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


async def get_ingest_events(
    since_timestamp: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Generate Server-Sent Events for ingest progress updates using Redis pub/sub.

    This subscribes to the Redis pub/sub channel for real-time ingest events
    and streams them to the client without polling.

    Args:
        since_timestamp: ISO timestamp string - only send events after this time (for reconnection)
    """
    from datetime import datetime, timezone

    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    redis_conn = None
    pubsub = None

    try:
        # Connect to Redis
        redis_conn = redis.from_url(redis_url)
        pubsub = redis_conn.pubsub()

        # Subscribe to the ingest events channel
        await asyncio.get_event_loop().run_in_executor(
            None, pubsub.subscribe, INGEST_EVENTS_CHANNEL
        )

        logger.info(
            "SSE client subscribed to channel",
            operation="get_ingest_events",
            channel=INGEST_EVENTS_CHANNEL
        )

        # Send initial connection confirmation
        yield f"data: {json.dumps({'type': 'connected', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"

        # Parse since_timestamp if provided for filtering
        since_dt = None
        if since_timestamp:
            try:
                since_dt = datetime.fromisoformat(
                    since_timestamp.replace("Z", "+00:00")
                )
                logger.info(
                    "SSE client resuming from timestamp",
                    operation="get_ingest_events",
                    since_timestamp=since_dt.isoformat()
                )
            except ValueError:
                logger.warning(
                    "Invalid since_timestamp format",
                    operation="get_ingest_events",
                    since_timestamp=since_timestamp,
                    error_type="timestamp_parse_error"
                )

        # Main event loop
        while True:
            try:
                # Get message from Redis pub/sub (with timeout)
                message = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: pubsub.get_message(timeout=30.0)
                )

                if message is None:
                    # Timeout reached, send heartbeat
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                    continue

                # Skip subscription confirmation messages
                if message["type"] != "message":
                    continue

                try:
                    # Parse the event data
                    event_data = json.loads(message["data"])

                    # Filter events based on since_timestamp if provided
                    if since_dt:
                        try:
                            event_timestamp = datetime.fromisoformat(
                                event_data["timestamp"].replace("Z", "+00:00")
                            )
                            if event_timestamp <= since_dt:
                                continue  # Skip old events
                        except (KeyError, ValueError):
                            pass  # If timestamp parsing fails, send the event anyway

                    # Convert our internal event format to the format expected by frontend
                    sse_event = {
                        "type": "media_ingested",  # Keep this for backward compatibility
                        "event_type": event_data.get("event_type"),
                        "timestamp": event_data.get("timestamp"),
                        "media_object": event_data.get("media_object"),
                        "error": event_data.get("error"),
                    }

                    # For backward compatibility, also include top-level fields
                    if event_data.get("media_object"):
                        media_obj = event_data["media_object"]
                        sse_event.update(
                            {
                                "object_key": media_obj.get("object_key"),
                                "has_thumbnail": media_obj.get("has_thumbnail"),
                                "ingestion_status": media_obj.get("ingestion_status"),
                            }
                        )

                    logger.debug(
                        "Forwarding SSE event",
                        operation="get_ingest_events",
                        event_type=event_data.get("event_type"),
                        object_key=sse_event.get("object_key")
                    )

                    # Send event to client
                    yield f"data: {json.dumps(sse_event)}\n\n"

                except json.JSONDecodeError as e:
                    logger.error(
                        "Failed to parse Redis event data",
                        operation="get_ingest_events",
                        error=str(e),
                        error_type="json_decode_error"
                    )
                    continue
                except Exception as e:
                    logger.error(
                        "Error processing Redis event",
                        operation="get_ingest_events",
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    continue

            except redis.ConnectionError:
                logger.error(
                    "Redis connection lost in SSE stream",
                    operation="get_ingest_events",
                    error_type="redis_connection_error"
                )
                yield f"data: {json.dumps({'type': 'error', 'message': 'Redis connection lost'})}\n\n"
                break
            except Exception as e:
                logger.error(
                    "Error in ingest events stream",
                    operation="get_ingest_events",
                    error=str(e),
                    error_type=type(e).__name__
                )
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                await asyncio.sleep(5)  # Wait before retrying

    except Exception as e:
        logger.error(
            "Failed to initialize ingest events stream",
            operation="get_ingest_events",
            error=str(e),
            error_type=type(e).__name__
        )
        yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to initialize stream'})}\n\n"
    finally:
        # Clean up Redis connections
        if pubsub:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, pubsub.unsubscribe, INGEST_EVENTS_CHANNEL
                )
                await asyncio.get_event_loop().run_in_executor(None, pubsub.close)
            except Exception as e:
                logger.warning(
                    "Error closing pub/sub connection",
                    operation="get_ingest_events",
                    phase="cleanup",
                    error=str(e),
                    error_type=type(e).__name__
                )

        if redis_conn:
            try:
                await asyncio.get_event_loop().run_in_executor(None, redis_conn.close)
            except Exception as e:
                logger.warning(
                    "Error closing Redis connection",
                    operation="get_ingest_events",
                    phase="cleanup",
                    error=str(e),
                    error_type=type(e).__name__
                )

        logger.info(
            "SSE connection closed",
            operation="get_ingest_events",
            phase="cleanup"
        )


@router.get("/ingest", response_class=StreamingResponse)
async def stream_ingest_events(
    since: Optional[str] = None,
    _: schemas.User = Depends(get_current_user),
):
    """
    Stream real-time ingest progress events via Server-Sent Events.

    This endpoint provides a persistent connection that streams updates
    when media objects are queued, started, or complete ingestion processing.

    Events include:
    - media_ingested: When a media object status changes (queued/started/complete)
    - connected: Initial connection confirmation
    - heartbeat: Periodic keep-alive messages
    - error: When errors occur in the stream

    Args:
        since: ISO timestamp - only send events after this time (for reconnection)
    """

    async def generate_events():
        """Async generator that properly reuses the existing event loop."""
        async for event in get_ingest_events(since_timestamp=since):
            yield f"{event}\n"

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )
