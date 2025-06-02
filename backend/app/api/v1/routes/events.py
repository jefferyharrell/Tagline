"""
Server-Sent Events routes for real-time updates.

This module provides SSE endpoints for:
- Real-time ingest progress updates
- Media object completion notifications
"""

import asyncio
import json
import logging
import os
from typing import AsyncGenerator

import redis
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from rq import Queue
from rq.job import Job

from app import auth_schemas as schemas
from app.auth_utils import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_ingest_events() -> AsyncGenerator[str, None]:
    """
    Generate Server-Sent Events for ingest progress updates.
    
    This monitors the Redis queue for completed ingest jobs and streams
    updates when media objects are successfully processed.
    """
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    try:
        redis_conn = redis.from_url(redis_url)
        ingest_queue = Queue("ingest", connection=redis_conn)
        
        # Keep track of processed jobs to avoid duplicates
        processed_jobs = set()
        
        while True:
            try:
                # Get completed jobs from the queue
                finished_jobs = ingest_queue.finished_job_registry
                
                for job_id in finished_jobs.get_job_ids():
                    if job_id not in processed_jobs:
                        try:
                            job = Job.fetch(job_id, connection=redis_conn)
                            
                            # Check if job completed successfully
                            if job.is_finished and not job.is_failed:
                                # Extract media object info from job args or kwargs
                                stored_media_object = None
                                
                                # Try to get from positional args first
                                if hasattr(job, 'args') and job.args:
                                    stored_media_object = job.args[0]
                                # If not in args, try kwargs
                                elif hasattr(job, 'kwargs') and job.kwargs and 'stored_media_object' in job.kwargs:
                                    stored_media_object = job.kwargs['stored_media_object']
                                
                                if stored_media_object:
                                    # Create event data
                                    event_data = {
                                        "type": "media_ingested",
                                        "object_key": getattr(stored_media_object, 'object_key', None),
                                        "job_id": job_id,
                                        "timestamp": job.ended_at.isoformat() if job.ended_at else None
                                    }
                                    
                                    # Send SSE event
                                    yield f"data: {json.dumps(event_data)}\n\n"
                                    
                                processed_jobs.add(job_id)
                                
                        except Exception as e:
                            logger.error(f"Error processing job {job_id}: {e}")
                            continue
                
                # Also send periodic heartbeat to keep connection alive
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': asyncio.get_event_loop().time()})}\n\n"
                
                # Wait before checking again
                await asyncio.sleep(2)
                
            except redis.ConnectionError:
                logger.error("Redis connection lost in SSE stream")
                yield f"data: {json.dumps({'type': 'error', 'message': 'Connection lost'})}\n\n"
                break
            except Exception as e:
                logger.error(f"Error in ingest events stream: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                await asyncio.sleep(5)  # Wait longer on error
                
    except Exception as e:
        logger.error(f"Failed to initialize ingest events stream: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to initialize stream'})}\n\n"


@router.get("/ingest", response_class=StreamingResponse)
async def stream_ingest_events(
    _: schemas.User = Depends(get_current_user),
):
    """
    Stream real-time ingest progress events via Server-Sent Events.
    
    This endpoint provides a persistent connection that streams updates
    when media objects complete ingestion processing.
    
    Events include:
    - media_ingested: When a media object is successfully processed
    - heartbeat: Periodic keep-alive messages
    - error: When errors occur in the stream
    """
    
    def generate_events():
        """Synchronous wrapper for the async generator."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            async_gen = get_ingest_events()
            while True:
                try:
                    yield loop.run_until_complete(async_gen.__anext__())
                except StopAsyncIteration:
                    break
        finally:
            loop.close()

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