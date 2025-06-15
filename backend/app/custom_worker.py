"""
Custom RQ worker with structlog.

This module creates an RQ worker that uses our structlog configuration
instead of RQ's default logging setup.
"""

import logging
import sys

from rq import Worker

from app.config import get_settings
from app.structlog_config import configure_structlog


class StructlogWorker(Worker):
    """RQ Worker that uses structlog."""

    def configure_logging(self):
        """Override RQ's logging configuration to use structlog."""
        # Get settings
        settings = get_settings()

        # Configure structlog for this worker
        configure_structlog(
            service_name="tagline-ingest-worker",
            log_level=logging.INFO,
            log_format=settings.LOG_FORMAT,
        )

        # Configure RQ logger to use pure JSON output
        rq_logger = logging.getLogger("rq.worker")
        rq_logger.setLevel(logging.INFO)

        # Remove all RQ handlers that might add timestamps/formatting
        for handler in rq_logger.handlers[:]:
            rq_logger.removeHandler(handler)

        # Add our pure JSON handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        rq_logger.addHandler(handler)

        # Don't propagate to avoid duplicate logs
        rq_logger.propagate = False


def setup_custom_loghandlers(level=None, date_format=None, log_format=None):
    """Custom log handler setup that completely overrides RQ's logging with pure JSON output."""
    # Get settings
    settings = get_settings()

    # Configure structlog first
    configure_structlog(
        service_name="tagline-ingest-worker",
        log_level=level or logging.INFO,
        log_format=settings.LOG_FORMAT,
    )

    # Get the root logger and completely reset it for pure JSON output
    root_logger = logging.getLogger()
    root_logger.setLevel(level or logging.INFO)

    # Remove ALL existing handlers from root logger
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create a pure message handler (no timestamps, no level prefixes)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(handler)

    # Configure RQ logger specifically
    rq_logger = logging.getLogger("rq.worker")
    rq_logger.setLevel(level or logging.INFO)

    # Remove all RQ handlers
    for handler in rq_logger.handlers[:]:
        rq_logger.removeHandler(handler)

    # Don't propagate to prevent duplicate logs
    rq_logger.propagate = False

    return rq_logger
