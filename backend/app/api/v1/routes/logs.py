"""
Frontend logging routes for Tagline backend.

This module provides API endpoints for:
- Receiving log messages from frontend
- Echoing them to backend stdout for debugging
"""

from datetime import datetime, timezone
from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app import auth_schemas as schemas
from app.auth_utils import get_current_user
from app.structlog_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Log levels
LogLevel = Literal["debug", "info", "warn", "error"]


class LogEntry(BaseModel):
    """Single log entry from frontend."""

    level: LogLevel
    message: str
    timestamp: str
    component: str = "frontend"
    url: str = ""
    user_agent: str = ""
    extra: dict = {}


class LogBatch(BaseModel):
    """Batch of log entries from frontend."""

    logs: List[LogEntry]
    session_id: str = ""


@router.post("/")
async def submit_logs(
    log_batch: LogBatch,
    _: schemas.User = Depends(get_current_user),
):
    """
    Submit log entries from frontend to be echoed to backend stdout.

    This endpoint receives log messages from the frontend and echoes them
    to the backend's stdout for centralized logging and debugging.

    Args:
        log_batch: Batch of log entries to process

    Returns:
        Success confirmation
    """
    try:
        for log_entry in log_batch.logs:
            # Format the log message for stdout
            timestamp = log_entry.timestamp or datetime.now(timezone.utc).isoformat()
            component = log_entry.component or "frontend"
            url_info = f" [{log_entry.url}]" if log_entry.url else ""

            # Create formatted message
            formatted_message = (
                f"[FRONTEND-{log_entry.level.upper()}] "
                f"{timestamp} {component}{url_info}: {log_entry.message}"
            )

            # Add extra fields if present
            if log_entry.extra:
                extra_str = " | ".join([f"{k}={v}" for k, v in log_entry.extra.items()])
                formatted_message += f" | {extra_str}"

            # Echo to backend stdout using appropriate log level
            if log_entry.level == "debug":
                logger.debug(formatted_message)
            elif log_entry.level == "info":
                logger.info(formatted_message)
            elif log_entry.level == "warn":
                logger.warning(formatted_message)
            elif log_entry.level == "error":
                logger.error(formatted_message)
            else:
                logger.info(formatted_message)  # Default to info

        return {
            "status": "success",
            "processed": len(log_batch.logs),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Error processing frontend logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process logs: {str(e)}",
        )


@router.get("/health")
async def logs_health():
    """
    Health check endpoint for logging service.

    Returns:
        Simple health status
    """
    return {
        "status": "healthy",
        "service": "frontend-logging",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
