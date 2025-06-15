"""
Worker startup configuration for structured logging.

This module configures the logging system for RQ workers to use
structlog for high-performance structured logging when processing ingest tasks.
"""

import logging
import os
import sys

from app.structlog_config import configure_structlog, get_logger


def configure_worker_logging():
    """
    Configure structlog for RQ workers.
    
    This should be called when the worker starts up to ensure
    all log output uses high-performance structured logging.
    """
    # Get log level from environment or default to INFO
    log_level_str = os.getenv("LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    # Set up structlog with ingest-worker service name
    configure_structlog(
        service_name="tagline-ingest-worker",
        log_level=log_level,
        development_mode=False  # Always use JSON output for workers
    )
    
    # Log startup message
    logger = get_logger(__name__)
    logger.info("Ingest worker started with structlog configured",
                operation="worker_startup",
                log_level=log_level_str,
                pid=os.getpid())
    
    # Also print to stderr to verify it's being called
    print(f"Structlog configured at level {log_level_str}", file=sys.stderr)


if __name__ == "__main__":
    # If run directly, configure logging
    configure_worker_logging()