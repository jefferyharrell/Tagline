"""
Custom RQ worker with JSON logging.

This module creates an RQ worker that uses our JSON logging configuration
instead of RQ's default logging setup.
"""

import logging
import sys
from rq import Worker
from rq.logutils import setup_loghandlers

from app.json_logging import JSONFormatter


class JSONLoggingWorker(Worker):
    """RQ Worker that uses JSON logging."""
    
    def configure_logging(self):
        """Override RQ's logging configuration to use JSON format."""
        # Get the RQ logger
        logger = logging.getLogger('rq.worker')
        logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        logger.handlers = []
        
        # Create handler with JSON formatter
        handler = logging.StreamHandler(sys.stdout)
        formatter = JSONFormatter(service_name="tagline-ingest-worker")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Also configure the root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.handlers = []
        root_logger.addHandler(handler)
        
        # Don't propagate to avoid duplicate logs
        logger.propagate = False


def setup_custom_loghandlers(level=None, date_format=None, log_format=None):
    """Custom log handler setup that uses JSON formatting."""
    # This function is called by RQ, we override it to use JSON
    logger = logging.getLogger('rq.worker')
    logger.setLevel(level or logging.INFO)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    formatter = JSONFormatter(service_name="tagline-ingest-worker")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Don't propagate
    logger.propagate = False
    
    return logger