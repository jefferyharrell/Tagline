"""
Custom RQ worker with structlog.

This module creates an RQ worker that uses our structlog configuration
instead of RQ's default logging setup.
"""

import logging
import sys
from rq import Worker
from rq.logutils import setup_loghandlers

from app.structlog_config import configure_structlog, get_logger


class StructlogWorker(Worker):
    """RQ Worker that uses structlog."""
    
    def configure_logging(self):
        """Override RQ's logging configuration to use structlog."""
        # Configure structlog for this worker
        configure_structlog(
            service_name="tagline-ingest-worker",
            log_level=logging.INFO,
            development_mode=False
        )
        
        # Get the RQ logger and make it use our configuration
        logger = logging.getLogger('rq.worker')
        logger.setLevel(logging.INFO)
        
        # Don't propagate to avoid duplicate logs
        logger.propagate = False


def setup_custom_loghandlers(level=None, date_format=None, log_format=None):
    """Custom log handler setup that uses structlog formatting."""
    # This function is called by RQ, we override it to use structlog
    configure_structlog(
        service_name="tagline-ingest-worker",
        log_level=level or logging.INFO,
        development_mode=False
    )
    
    logger = logging.getLogger('rq.worker')
    logger.setLevel(level or logging.INFO)
    
    # Don't propagate
    logger.propagate = False
    
    return logger