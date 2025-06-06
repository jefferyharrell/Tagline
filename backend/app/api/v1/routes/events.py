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
from typing import AsyncGenerator, Optional

import redis
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from rq import Queue
from rq.job import Job

from app import auth_schemas as schemas
from app.auth_utils import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_ingest_events(since_timestamp: Optional[str] = None) -> AsyncGenerator[str, None]:
    """
    Generate Server-Sent Events for ingest progress updates.
    
    This monitors the Redis queue for completed ingest jobs and streams
    updates when media objects are successfully processed.
    
    Args:
        since_timestamp: ISO timestamp string - only send events for jobs completed after this time
    """
    from datetime import datetime, timezone, timedelta
    
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    try:
        redis_conn = redis.from_url(redis_url)
        ingest_queue = Queue("ingest", connection=redis_conn)
        
        # Keep track of processed jobs to avoid duplicates
        processed_jobs = set()
        
        # For this simpler approach, we'll only send heartbeats and wait for truly new job completions
        # We'll monitor the queue for jobs that transition to finished state while we're watching
        connection_start_time = datetime.now(timezone.utc)
        logger.info(f"SSE connection started at {connection_start_time}, monitoring for newly completed jobs")
        
        # Get current finished job IDs to establish baseline
        baseline_finished_jobs = set(ingest_queue.finished_job_registry.get_job_ids())
        logger.info(f"Baseline: {len(baseline_finished_jobs)} jobs already finished, will ignore these")
        
        while True:
            try:
                # Get current finished jobs
                current_finished_jobs = set(ingest_queue.finished_job_registry.get_job_ids())
                
                # Find newly finished jobs (jobs that weren't in baseline)
                newly_finished = current_finished_jobs - baseline_finished_jobs - processed_jobs
                
                for job_id in newly_finished:
                    try:
                        job = Job.fetch(job_id, connection=redis_conn)
                        
                        # Check if job completed successfully
                        if job.is_finished and not job.is_failed:
                            # Extract object_key from job args
                            object_key = None
                            
                            # The ingest function takes object_key as first positional argument
                            if hasattr(job, 'args') and job.args:
                                object_key = job.args[0]
                            
                            if object_key:
                                # Query database to get current status of the media object
                                from app.db.database import get_db
                                from app.db.repositories.media_object import MediaObjectRepository
                                
                                db_gen = get_db()
                                db = next(db_gen)
                                try:
                                    repo = MediaObjectRepository(db)
                                    media_obj = repo.get_by_object_key(object_key)
                                    
                                    if media_obj:
                                        # Create event data with proper fields
                                        event_data = {
                                            "type": "media_ingested",
                                            "object_key": object_key,
                                            "has_thumbnail": media_obj.has_thumbnail,
                                            "ingestion_status": media_obj.ingestion_status or "completed",
                                            "job_id": job_id,
                                            "timestamp": job.ended_at.isoformat() if job.ended_at else None
                                        }
                                        
                                        logger.info(f"Sending SSE event for newly completed job {object_key}: {event_data}")
                                        
                                        # Send SSE event
                                        yield f"data: {json.dumps(event_data)}\n\n"
                                finally:
                                    # Ensure proper cleanup of database session
                                    try:
                                        next(db_gen)
                                    except StopIteration:
                                        pass
                            
                            # Always mark job as processed, regardless of success/failure
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
    since: Optional[str] = None,
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
            async_gen = get_ingest_events(since_timestamp=since)
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