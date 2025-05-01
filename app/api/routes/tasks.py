import os

import redis
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from redis.exceptions import ConnectionError
from rq import Queue

from app.tasks.ingest import ingest_orchestrator

router = APIRouter()

INGEST_TIMEOUT = 10800  # 3 hours


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
        lock = r.lock("ingest:lock", timeout=INGEST_TIMEOUT)
        if lock.locked():
            return JSONResponse(
                {"status": "already_running"}, status_code=status.HTTP_409_CONFLICT
            )
        q = Queue(connection=r)
        job = q.enqueue(ingest_orchestrator, redis_url=redis_url)
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
