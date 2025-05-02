import os

import redis
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from redis.exceptions import ConnectionError
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from app.tasks.ingest_orchestrator import ingest_orchestrator

router = APIRouter()

ORCHESTRATOR_JOB_ID = "orchestrator-singleton-job"


@router.post(
    "/tasks/ingest",
    tags=["tasks"],
    summary="Trigger ingest orchestrator",
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_ingest():
    """
    Trigger the ingest orchestrator task. Checks idempotency via Redis lock. If already running, returns 409.
    Otherwise, enqueues the orchestrator and returns the job ID.
    """
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        r = redis.from_url(redis_url)
        r.ping()
        orchestrator_queue = Queue("orchestrator", connection=r)
        from rq.job import Job

        try:
            existing_job = Job.fetch(ORCHESTRATOR_JOB_ID, connection=r)
            if existing_job.get_status() in ("queued", "started", "deferred"):
                return JSONResponse(
                    {"status": "already_running"}, status_code=status.HTTP_409_CONFLICT
                )
        except Exception:
            # Job doesn't exist or can't be fetched, so it's safe to enqueue
            pass
        job = orchestrator_queue.enqueue(
            ingest_orchestrator, redis_url=redis_url, job_id=ORCHESTRATOR_JOB_ID
        )
        return JSONResponse(
            {"status": "enqueued", "job_id": job.id},
            status_code=status.HTTP_202_ACCEPTED,
        )
    except ConnectionError:
        return JSONResponse(
            {"status": "error", "message": "Could not connect to Redis"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get(
    "/v1/ingest/status",
    tags=["tasks"],
    summary="Get ingest orchestrator status",
)
def get_ingest_status():
    """
    Get the status and progress of the current or last run ingest orchestrator task.
    """
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        r = redis.from_url(redis_url)
        r.ping()

        job = Job.fetch(ORCHESTRATOR_JOB_ID, connection=r)

        job_status = job.get_status()
        metadata = job.meta

        # Add failure reason if applicable
        if job_status == "failed":
            metadata["failure_reason"] = job.exc_info

        return JSONResponse(
            {
                "job_id": job.id,
                "status": job_status,
                "metadata": metadata,
                "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            }
        )

    except NoSuchJobError:
        return JSONResponse(
            {"status": "not_found", "message": "Ingest job not found."},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    except ConnectionError:
        return JSONResponse(
            {"status": "error", "message": "Could not connect to Redis"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
