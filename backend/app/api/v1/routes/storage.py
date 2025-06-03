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
from app.storage_provider import get_storage_provider
from app.storage_providers.base import StorageProviderBase
from app.schemas import MediaObject, PaginatedMediaResponse

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
        
        # Get directory listing from storage provider
        items = storage_provider.list_directory(prefix=path)
        
        # Separate folders and files
        folders = [item for item in items if item.is_folder]
        files = [item for item in items if not item.is_folder]
        
        # Initialize repository and Redis for queueing
        media_repo = MediaObjectRepository(db)
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        redis_conn = redis.from_url(redis_url)
        ingest_queue = Queue("ingest", connection=redis_conn)
        
        # Supported media file extensions
        SUPPORTED_MEDIA_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.mp4', '.mov', '.avi'}
        
        # Process each file - create MediaObject if needed
        for file_item in files:
            if file_item.object_key:
                # Check if it's a supported media file
                file_ext = file_item.object_key.lower().split('.')[-1] if '.' in file_item.object_key else ''
                if f'.{file_ext}' in SUPPORTED_MEDIA_EXTENSIONS:
                    # Check if MediaObject already exists
                    existing_media = media_repo.get_by_object_key(file_item.object_key)
                    
                    if not existing_media:
                        # Create a sparse MediaObject record
                        logger.info(f"Discovering new media file: {file_item.object_key}")
                        
                        # Parse last_modified if available
                        file_last_modified = None
                        if file_item.last_modified:
                            try:
                                file_last_modified = datetime.fromisoformat(file_item.last_modified.replace('Z', '+00:00'))
                            except:
                                pass
                        
                        # Create sparse MediaObject
                        media_obj = media_repo.create_sparse(
                            object_key=file_item.object_key,
                            file_size=file_item.size,
                            file_mimetype=file_item.mimetype,
                            file_last_modified=file_last_modified
                        )
                        
                        if media_obj:
                            # Queue ingestion task
                            try:
                                ingest_queue.enqueue(
                                    "app.tasks.ingest.ingest", 
                                    object_key=file_item.object_key
                                )
                                logger.info(f"Queued ingestion for: {file_item.object_key}")
                            except Exception as e:
                                logger.error(f"Failed to queue ingestion for {file_item.object_key}: {e}")
        
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