import logging
import os
from logging.config import dictConfig

import redis
from rq import Worker

# Define a basic logging config here
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",  # Log to stdout
        },
    },
    "root": {
        "handlers": ["default"],
        # Level will be set below from env var
        "level": "INFO",
    },
    # You might want to configure RQ's internal loggers too
    "loggers": {
        "rq.worker": {
            "handlers": ["default"],
            "level": "WARNING",  # Example: Keep RQ's own logs less verbose
            "propagate": False,
        },
    },
}

if __name__ == "__main__":
    # Get log level from environment, default to INFO
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    # Update the root logger level in the config
    LOGGING_CONFIG["root"]["level"] = log_level

    # Configure logging for the worker process
    dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)
    logger.info(f"Starting RQ worker with logging level set to {log_level}.")

    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    conn = redis.from_url(redis_url)
    queue_names = os.environ.get("RQ_QUEUES", "default").split(",")

    worker = Worker(queue_names, connection=conn)
    worker.work()
