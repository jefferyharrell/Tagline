"""
Admin routes for Tagline backend.

This module provides administrative endpoints for:
- Media ingestion orchestration
- System management tasks
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

import redis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis.exceptions import ConnectionError
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job
from slowapi import Limiter
from slowapi.util import get_remote_address

from app import auth_schemas as schemas
from app.auth_utils import get_current_admin
from app.tasks.ingest_orchestrator import ingest_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()

# Create a separate limiter for admin endpoints
limiter = Limiter(key_func=get_remote_address)

ORCHESTRATOR_JOB_ID = "orchestrator-singleton-job"


class IngestStartRequest(BaseModel):
    """Request model for starting ingest orchestration."""
    path: Optional[str] = None
    dry_run: bool = False


class IngestStatusResponse(BaseModel):
    """Response model for ingest status."""
    job_id: str
    status: str
    metadata: dict
    enqueued_at: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    duration_seconds: Optional[float] = None


class IngestHistoryItem(BaseModel):
    """Model for ingest history items."""
    job_id: str
    status: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    total_items: int = 0
    processed_items: int = 0
    queued_items: int = 0


@router.post(
    "/ingest/start",
    tags=["admin"],
    summary="Start media ingest orchestration",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=dict,
)
@limiter.limit("1/hour")
async def start_ingest(
    request: Request,
    ingest_request: IngestStartRequest,
    _: schemas.User = Depends(get_current_admin),
):
    """
    Start the ingest orchestrator to scan and process all media files.
    
    This endpoint is rate-limited to 1 request per hour to prevent abuse.
    If orchestration is already running, returns 409 Conflict.
    
    Args:
        request: HTTP request object (for rate limiting)
        ingest_request: Ingest start parameters
        
    Returns:
        Status and job ID if successfully enqueued
    """
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        r = redis.from_url(redis_url)
        r.ping()
        orchestrator_queue = Queue("orchestrator", connection=r)
        
        # Check if orchestrator is already running
        try:
            existing_job = Job.fetch(ORCHESTRATOR_JOB_ID, connection=r)
            if existing_job.get_status() in ("queued", "started", "deferred"):
                # Calculate how long it's been running
                duration = None
                if existing_job.started_at:
                    duration = (datetime.now(timezone.utc) - existing_job.started_at).total_seconds()
                
                return JSONResponse(
                    {
                        "status": "already_running",
                        "job_id": existing_job.id,
                        "started_at": existing_job.started_at.isoformat() if existing_job.started_at else None,
                        "duration_seconds": duration,
                    },
                    status_code=status.HTTP_409_CONFLICT
                )
        except NoSuchJobError:
            # Job doesn't exist, safe to enqueue
            pass
        except Exception as e:
            logger.warning(f"Error checking existing job: {e}")
            # Continue anyway
            
        # Enqueue the orchestrator with parameters
        job = orchestrator_queue.enqueue(
            ingest_orchestrator,
            redis_url=redis_url,
            path_filter=ingest_request.path,
            dry_run=ingest_request.dry_run,
            job_id=ORCHESTRATOR_JOB_ID,
            job_timeout=3600,  # 1 hour timeout
        )
        
        logger.info(f"Enqueued ingest orchestrator job {job.id} with path_filter={ingest_request.path}, dry_run={ingest_request.dry_run}")
        
        return JSONResponse(
            {
                "status": "enqueued",
                "job_id": job.id,
                "path_filter": ingest_request.path,
                "dry_run": ingest_request.dry_run,
            },
            status_code=status.HTTP_202_ACCEPTED,
        )
        
    except ConnectionError:
        logger.error("Could not connect to Redis")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to job queue",
        )
    except Exception as e:
        logger.exception(f"Error starting ingest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/ingest/status",
    tags=["admin"],
    summary="Get current ingest orchestration status",
    response_model=IngestStatusResponse,
)
async def get_ingest_status(
    _: schemas.User = Depends(get_current_admin),
):
    """
    Get the status and progress of the current or last ingest orchestration.
    
    Returns detailed metadata including:
    - Current stage of processing
    - Number of items processed
    - Progress percentage
    - Error information if failed
    """
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        r = redis.from_url(redis_url)
        r.ping()
        
        job = Job.fetch(ORCHESTRATOR_JOB_ID, connection=r)
        
        job_status = job.get_status()
        metadata = job.meta.copy()
        
        # Add failure reason if applicable
        if job_status == "failed" and job.exc_info:
            metadata["failure_reason"] = job.exc_info
            
        # Calculate duration
        duration = None
        if job.started_at and job.ended_at:
            duration = (job.ended_at - job.started_at).total_seconds()
        elif job.started_at:
            duration = (datetime.now(timezone.utc) - job.started_at).total_seconds()
            
        return IngestStatusResponse(
            job_id=job.id,
            status=job_status.value if hasattr(job_status, 'value') else str(job_status),
            metadata=metadata,
            enqueued_at=job.enqueued_at.isoformat() if job.enqueued_at else None,
            started_at=job.started_at.isoformat() if job.started_at else None,
            ended_at=job.ended_at.isoformat() if job.ended_at else None,
            duration_seconds=duration,
        )
        
    except NoSuchJobError:
        # Return a "not found" status instead of 404
        return IngestStatusResponse(
            job_id=ORCHESTRATOR_JOB_ID,
            status="not_found",
            metadata={"message": "No ingest job has been run yet"},
            enqueued_at=None,
            started_at=None,
            ended_at=None,
            duration_seconds=None,
        )
    except ConnectionError:
        logger.error("Could not connect to Redis")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to job queue",
        )
    except Exception as e:
        logger.exception(f"Error getting ingest status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/ingest/cancel",
    tags=["admin"],
    summary="Cancel running ingest orchestration",
    response_model=dict,
)
async def cancel_ingest(
    _: schemas.User = Depends(get_current_admin),
):
    """
    Cancel a running ingest orchestration job.
    
    This will stop the orchestrator from queuing new items,
    but already queued ingest tasks will continue to run.
    """
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        r = redis.from_url(redis_url)
        r.ping()
        
        try:
            job = Job.fetch(ORCHESTRATOR_JOB_ID, connection=r)
            
            if job.get_status() not in ("queued", "started"):
                return JSONResponse(
                    {
                        "status": "not_running",
                        "job_status": job.get_status(),
                        "message": "Job is not currently running",
                    },
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
                
            # Cancel the job
            job.cancel()
            logger.info(f"Cancelled ingest orchestrator job {job.id}")
            
            return {
                "status": "cancelled",
                "job_id": job.id,
                "message": "Orchestrator cancelled. Already queued tasks will continue.",
            }
            
        except NoSuchJobError:
            return JSONResponse(
                {
                    "status": "not_found",
                    "message": "No ingest job to cancel",
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )
            
    except ConnectionError:
        logger.error("Could not connect to Redis")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to job queue",
        )
    except Exception as e:
        logger.exception(f"Error cancelling ingest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/ingest/history",
    tags=["admin"],
    summary="Get ingest orchestration history",
    response_model=list[IngestHistoryItem],
)
async def get_ingest_history(
    limit: int = 10,
    _: schemas.User = Depends(get_current_admin),
):
    """
    Get history of recent ingest orchestration runs.
    
    Note: This is a simplified version that only shows the current/last job.
    Future enhancement would store history in the database.
    """
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        r = redis.from_url(redis_url)
        r.ping()
        
        history = []
        
        try:
            job = Job.fetch(ORCHESTRATOR_JOB_ID, connection=r)
            
            duration = None
            if job.started_at and job.ended_at:
                duration = (job.ended_at - job.started_at).total_seconds()
            elif job.started_at:
                duration = (datetime.now(timezone.utc) - job.started_at).total_seconds()
                
            history_item = IngestHistoryItem(
                job_id=job.id,
                status=job.get_status().value if hasattr(job.get_status(), 'value') else str(job.get_status()),
                started_at=job.started_at.isoformat() if job.started_at else None,
                ended_at=job.ended_at.isoformat() if job.ended_at else None,
                duration_seconds=duration,
                total_items=job.meta.get("total_items", 0),
                processed_items=job.meta.get("processed_items", 0),
                queued_items=job.meta.get("queued_items", 0),
            )
            history.append(history_item)
            
        except NoSuchJobError:
            # No history yet
            pass
            
        return history
        
    except ConnectionError:
        logger.error("Could not connect to Redis")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to job queue",
        )
    except Exception as e:
        logger.exception(f"Error getting ingest history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )