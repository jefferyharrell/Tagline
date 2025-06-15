"""
Structlog configuration for structured logging in Tagline.

This module provides optimized structlog configuration with high-performance
JSON serialization, context management, and production-ready setup.
"""

import logging
import sys
from typing import Any, Dict

import structlog
import orjson


def orjson_serializer(obj: Any, **kwargs) -> str:
    """
    High-performance JSON serializer using orjson.
    
    Args:
        obj: Object to serialize
        **kwargs: Additional arguments (ignored for compatibility)
        
    Returns:
        JSON string
    """
    # orjson returns bytes, so we decode to string for compatibility
    return orjson.dumps(obj, option=orjson.OPT_UTC_Z).decode()


def add_service_name(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add service name to all log entries.
    
    Args:
        logger: The logger instance
        method_name: The method name being called
        event_dict: The event dictionary
        
    Returns:
        Updated event dictionary with service name
    """
    event_dict["service"] = getattr(logger, "_service_name", "tagline-backend")
    return event_dict


def add_module_info(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add module information to log entries.
    
    Args:
        logger: The logger instance  
        method_name: The method name being called
        event_dict: The event dictionary
        
    Returns:
        Updated event dictionary with module info
    """
    # Extract module name from logger name if available
    if hasattr(logger, "_context") and "logger_name" in logger._context:
        event_dict["module"] = logger._context["logger_name"]
    return event_dict


def configure_structlog(
    service_name: str = "tagline-backend",
    log_level: int = logging.INFO,
    development_mode: bool = False
) -> None:
    """
    Configure structlog with optimized settings for production or development.
    
    Args:
        service_name: Name of the service for log identification
        log_level: Logging level to set
        development_mode: Whether to use development-friendly output
    """
    # Configure processors based on environment
    if development_mode:
        # Development: human-readable output with colors
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            add_service_name,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=True)
        ]
        factory = structlog.stdlib.LoggerFactory()
    else:
        # Production: optimized JSON output
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            add_service_name,
            add_module_info,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(serializer=orjson_serializer)
        ]
        # Use standard LoggerFactory for compatibility
        factory = structlog.stdlib.LoggerFactory()
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=factory,
        context_class=dict,
        cache_logger_on_first_use=True,  # Performance optimization
    )
    
    # Configure standard library logging
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove all existing handlers to prevent duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create handler with pure message output (no timestamps/levels in production)
    handler = logging.StreamHandler(sys.stdout)
    if development_mode:
        # Development: keep some formatting for readability
        handler.setFormatter(logging.Formatter("%(message)s"))
    else:
        # Production: pure JSON output only
        handler.setFormatter(logging.Formatter("%(message)s"))
    
    root_logger.addHandler(handler)
    
    # Prevent propagation to avoid duplicate logs
    root_logger.propagate = False
    
    # Store service name for access in processors
    structlog.get_logger()._service_name = service_name


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Get a structlog logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Bound logger instance
    """
    logger = structlog.get_logger(name)
    
    # Add logger name to context for module identification
    if name:
        logger = logger.bind(logger_name=name)
    
    return logger


def get_job_logger(name: str = None, **context) -> structlog.BoundLogger:
    """
    Get a logger with job-specific context pre-bound.
    
    Args:
        name: Logger name (typically __name__)
        **context: Context to bind to the logger
        
    Returns:
        Bound logger with context
    """
    logger = get_logger(name)
    if context:
        logger = logger.bind(**context)
    return logger


# Compatibility functions for gradual migration
def setup_json_logging(
    service_name: str = "tagline-backend",
    log_level: int = logging.INFO
) -> None:
    """
    Compatibility function for existing setup_json_logging calls.
    Configures structlog instead of custom JSON logging.
    """
    configure_structlog(
        service_name=service_name,
        log_level=log_level,
        development_mode=False
    )


def get_context_logger(name: str) -> structlog.BoundLogger:
    """
    Compatibility function for existing get_context_logger calls.
    Returns a structlog bound logger.
    """
    return get_logger(name)