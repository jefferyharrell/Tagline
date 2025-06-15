#!/usr/bin/env python
"""
RQ worker startup script with structlog configuration.

This script configures structlog then runs the standard RQ command.
"""

import os
import sys
import subprocess

# Add app to Python path
sys.path.insert(0, '/app')

# Configure structlog before starting worker
from app.worker_setup import configure_worker_logging
from app.custom_worker import setup_custom_loghandlers

# Configure app-level structlog
configure_worker_logging()

# Override RQ's log setup function globally
import rq.logutils
rq.logutils.setup_loghandlers = setup_custom_loghandlers

# Also override the logger setup in rq.worker module
import rq.worker
rq.worker.setup_loghandlers = setup_custom_loghandlers

# Run RQ with the provided arguments
# This will use RQ's built-in worker pool functionality
# but with our structlog configured
if __name__ == '__main__':
    # Use subprocess to run rq with our modified environment
    cmd = ['rq'] + sys.argv[1:]
    sys.exit(subprocess.call(cmd))