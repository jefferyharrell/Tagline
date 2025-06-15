"""
JSON logging formatter and utilities for structured logging.

This module provides a JSON formatter for Python's logging module that outputs
structured logs with microsecond-precision timestamps and contextual data.
"""

import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.

    Outputs log records as JSON with microsecond-precision timestamps
    and structured context data.
    """

    def __init__(self, service_name: str = "tagline-backend"):
        """
        Initialize the JSON formatter.

        Args:
            service_name: Name of the service for log identification
        """
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as JSON.

        Args:
            record: The log record to format

        Returns:
            JSON string representation of the log record
        """
        # Create base log structure
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "service": self.service_name,
            "module": record.name,
        }

        # Add context if available
        context = {}

        # Extract custom context attributes
        for key, value in record.__dict__.items():
            # Skip standard LogRecord attributes
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "getMessage",
                "message",
            ]:
                context[key] = value

        # Add standard context
        context.update(
            {
                "function": record.funcName,
                "line": record.lineno,
                "file": record.filename,
            }
        )

        # Add exception info if present
        if record.exc_info:
            context["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Only add context if it has meaningful data
        if any(v is not None for v in context.values()):
            log_obj["context"] = context

        return json.dumps(log_obj, default=str)


class ContextLogger:
    """
    Wrapper around standard logger that allows adding persistent context.
    """

    def __init__(self, logger: logging.Logger):
        """
        Initialize with a standard logger.

        Args:
            logger: The underlying logger to wrap
        """
        self.logger = logger
        self.context: Dict[str, Any] = {}

    def add_context(self, **kwargs):
        """Add persistent context that will be included in all log messages."""
        self.context.update(kwargs)

    def clear_context(self):
        """Clear all persistent context."""
        self.context.clear()

    def _log(self, level: int, msg: str, **kwargs):
        """Internal log method that adds context to the log record."""
        extra = self.context.copy()
        extra.update(kwargs)
        self.logger.log(level, msg, extra=extra)

    def debug(self, msg: str, **kwargs):
        """Log a debug message with context."""
        self._log(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs):
        """Log an info message with context."""
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        """Log a warning message with context."""
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs):
        """Log an error message with context."""
        self._log(logging.ERROR, msg, **kwargs)

    def critical(self, msg: str, **kwargs):
        """Log a critical message with context."""
        self._log(logging.CRITICAL, msg, **kwargs)

    def exception(self, msg: str, **kwargs):
        """Log an exception with context."""
        extra = self.context.copy()
        extra.update(kwargs)
        self.logger.exception(msg, extra=extra, exc_info=True)


def setup_json_logging(
    service_name: str = "tagline-backend", log_level: int = logging.INFO
) -> None:
    """
    Configure the root logger to use JSON formatting.

    Args:
        service_name: Name of the service for log identification
        log_level: Logging level to set
    """
    # Create JSON formatter
    formatter = JSONFormatter(service_name=service_name)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add new handler with JSON formatter
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


def get_context_logger(name: str) -> ContextLogger:
    """
    Get a context-aware logger for the given module.

    Args:
        name: Module name (typically __name__)

    Returns:
        ContextLogger instance
    """
    return ContextLogger(logging.getLogger(name))
