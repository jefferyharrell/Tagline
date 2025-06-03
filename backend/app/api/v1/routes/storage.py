"""
Storage browsing routes for Tagline backend.

This module provides API endpoints for:
- Browsing storage folders and files
- Triggering background ingestion for discovered media files
"""

import logging
import os
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
import redis
from pydantic import BaseModel
from rq import Queue
from sqlalchemy.orm import Session

from app import auth_schemas as schemas
from app.auth_utils import get_current_user
from app.db.database import get_db
from app.db.repositories.media_object import MediaObjectRepository
from app.media_processing.factory import is_extension_supported
from app.storage_provider import get_storage_provider

# Import processor modules to trigger registration via decorators
# The noqa comment prevents linters from flagging unused import, which is needed here.
from app.media_processing import heicprocessor  # noqa: F401
from app.media_processing import jpegprocessor  # noqa: F401
from app.media_processing import pngprocessor   # noqa: F401
from app.storage_providers.base import StorageProviderBase
from app.schemas import MediaObject
from app.tasks.ingest import ingest

logger = logging.getLogger(__name__)

router = APIRouter()


class DirectoryItemResponse(BaseModel):
    """Response model for directory items."""
    name: str
    is_folder: bool
    object_key: Optional[str] = None
    size: Optional[int] = None
    last_modified: Optional[str] = None
    mimetype: Optional[str] = None


class BrowseResponse(BaseModel):
    """Response model for browse endpoint."""
    folders: List[DirectoryItemResponse]
    media_objects: List[MediaObject]  # All media objects (ingested + pending)
    total: int  # Total count of media objects
    limit: int
    offset: int
    has_more: bool


@router.get("/browse", response_model=BrowseResponse)
async def browse_storage(
    path: Optional[str] = None,
    limit: int = 36,
    offset: int = 0,
    storage_provider: StorageProviderBase = Depends(get_storage_provider),
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_user),
):
    """Browse storage folders and files at the given path.
    
    Creates MediaObject records for any new files discovered and queues them for ingestion.
    Returns folders and ALL media objects (both ingested and pending) in the current path.
    
    Args:
        path: Directory path to browse (None for root)
        limit: Maximum number of media objects to return
        offset: Number of media objects to skip
        storage_provider: Storage provider instance
        db: Database session
        
    Returns:
        BrowseResponse with folders and paginated MediaObjects
    """
    try:
        logger.info(f"Browsing storage path: {path}, limit={limit}, offset={offset}")
        
        # Initialize repository and Redis for queueing
        media_repo = MediaObjectRepository(db)
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        redis_conn = redis.from_url(redis_url)
        ingest_queue = Queue("ingest", connection=redis_conn)
        
        # Get directory listing from storage provider (fastest, most efficient)
        items = storage_provider.list_directory(prefix=path)
        
        # Separate folders and files
        folders = [item for item in items if item.is_folder]
        files = [item for item in items if not item.is_folder]
        
        # Process discovered files: create MediaObjects and queue ingest tasks
        newly_queued = 0
        for file_item in files:
            if not file_item.object_key:
                continue
                
            # Check if it's a supported media file using dynamic processor registry
            _, ext = os.path.splitext(file_item.object_key.lower())
            if not is_extension_supported(ext):
                continue
                
            # Parse file metadata
            file_last_modified = None
            if file_item.last_modified:
                try:
                    file_last_modified = datetime.fromisoformat(file_item.last_modified.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Could not parse last_modified for {file_item.object_key}: {file_item.last_modified}")
            
            # Create sparse MediaObject record (with ON CONFLICT DO NOTHING behavior)
            media_obj = media_repo.create_sparse(
                object_key=file_item.object_key,
                file_size=file_item.size,
                file_mimetype=file_item.mimetype,
                file_last_modified=file_last_modified
            )
            
            # If this is a newly created MediaObject, queue it for ingestion
            if media_obj and media_obj.ingestion_status == 'pending':
                try:
                    # Check if we just created this (created_at very recent)
                    if media_obj.created_at:
                        time_since_creation = datetime.utcnow() - media_obj.created_at
                        if time_since_creation.total_seconds() < 5:  # Created within last 5 seconds
                            job = ingest_queue.enqueue(ingest, media_obj.object_key)
                            logger.info(f"Queued ingest job {job.id} for newly discovered file: {file_item.object_key}")
                            newly_queued += 1
                except Exception as e:
                    logger.error(f"Failed to queue ingest job for {file_item.object_key}: {e}")
        
        if newly_queued > 0:
            logger.info(f"Queued {newly_queued} new files for ingestion")
        
        # Now get all MediaObjects for this path with pagination
        # Build the prefix for exact folder matching
        # For root level, we pass None to get a special handling in the repository
        prefix_filter = f"{path}/" if path else None
        
        # Get paginated MediaObjects
        media_objects = media_repo.get_all(
            limit=limit,
            offset=offset,
            prefix=prefix_filter
        )
        
        # Get total count for pagination
        total_count = media_repo.count(prefix=prefix_filter)
        
        # Convert to response models
        folder_responses = [
            DirectoryItemResponse(
                name=folder.name,
                is_folder=folder.is_folder,
                object_key=folder.object_key,
                size=folder.size,
                last_modified=folder.last_modified,
                mimetype=folder.mimetype,
            )
            for folder in folders
        ]
        
        # Convert MediaObjectRecords to Pydantic models
        media_object_responses = [obj.to_pydantic() for obj in media_objects]
        
        logger.info(f"Browse complete: {len(folders)} folders, {len(media_object_responses)} media objects returned")
        
        return BrowseResponse(
            folders=folder_responses,
            media_objects=media_object_responses,
            total=total_count,
            limit=limit,
            offset=offset,
            has_more=(offset + len(media_object_responses)) < total_count,
        )
        
    except Exception as e:
        logger.error(f"Error browsing storage path {path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to browse storage: {str(e)}"
        )