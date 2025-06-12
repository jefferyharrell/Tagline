"""
Admin routes for Tagline backend.

This module provides administrative endpoints for:
- System management tasks
"""

import logging
from fastapi import APIRouter

from app import auth_schemas as schemas
from app.auth_utils import get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter()

# Future admin endpoints can be added here