"""
Worker startup configuration for JSON logging.

This module configures the logging system for RQ workers to use
JSON structured logging when processing ingest tasks.
"""

import logging
import os
import sys

from app.json_logging import setup_json_logging


def configure_worker_logging():
    """
    Configure JSON logging for RQ workers.
    
    This should be called when the worker starts up to ensure
    all log output uses structured JSON format.
    """
    # Get log level from environment or default to INFO
    log_level_str = os.getenv("LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    # Set up JSON logging with ingest-worker service name
    setup_json_logging(
        service_name="tagline-ingest-worker",
        log_level=log_level
    )
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("Ingest worker started with JSON logging configured",
                extra={
                    "operation": "worker_startup",
                    "log_level": log_level_str,
                    "pid": os.getpid()
                })
    
    # Also print to stderr to verify it's being called
    print(f"JSON logging configured at level {log_level_str}", file=sys.stderr)


if __name__ == "__main__":
    # If run directly, configure logging
    configure_worker_logging()