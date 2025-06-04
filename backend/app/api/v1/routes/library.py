"""
Library browsing routes for Tagline backend.

This module provides API endpoints for:
- Browsing the media library folder structure
- Getting media objects in specific folders
- Folder navigation and hierarchy
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


class FolderInfo(BaseModel):
    """Response model for folder information."""
    name: str
    path: str
    parent_path: Optional[str]
    item_count: int = 0
    total_size: int = 0


class FoldersResponse(BaseModel):
    """Response model for folders endpoint."""
    folders: List[FolderInfo]
    current_path: Optional[str]
    parent_path: Optional[str]


class MediaByFolderResponse(BaseModel):
    """Response model for media objects in a specific folder."""
    media_objects: List[MediaObject]
    folder_path: Optional[str]
    total: int


@router.get("", response_model=BrowseResponse)
@router.get("/{path:path}", response_model=BrowseResponse)
async def browse_library(
    path: Optional[str] = None,
    limit: int = 36,
    offset: int = 0,
    storage_provider: StorageProviderBase = Depends(get_storage_provider),
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_user),
):
    """Browse library folders and files at the given path.
    
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
    import time
    start_time = time.time()
    
    try:
        logger.info(f"Browsing library path: {path}, limit={limit}, offset={offset}")
        
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
        
        end_time = time.time()
        logger.info(f"Browse complete: {len(folders)} folders, {len(media_object_responses)} media objects returned in {end_time - start_time:.2f}s")
        
        return BrowseResponse(
            folders=folder_responses,
            media_objects=media_object_responses,
            total=total_count,
            limit=limit,
            offset=offset,
            has_more=(offset + len(media_object_responses)) < total_count,
        )
        
    except Exception as e:
        logger.error(f"Error browsing library path {path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to browse library: {str(e)}"
        )


@router.get("/folders/{path:path}", response_model=FoldersResponse)
@router.get("/folders", response_model=FoldersResponse, include_in_schema=False)
async def get_library_folders(
    path: Optional[str] = None,
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_user),
):
    """Get folder structure at the given path.
    
    This endpoint returns only folders (no files) and includes metadata about each folder.
    It's optimized for building folder tree views and navigation.
    
    Args:
        path: Directory path to list folders from (None or empty for root)
        db: Database session
        
    Returns:
        FoldersResponse with folder information and navigation helpers
    """
    try:
        # Normalize path
        if path == "" or path == "/":
            path = None
            
        logger.info(f"Getting library folders at path: {path}")
        
        # Initialize repository
        media_repo = MediaObjectRepository(db)
        
        # Build prefix for queries
        prefix = f"{path}/" if path else ""
        
        # Get immediate subfolders
        subfolder_names = media_repo.get_subfolders_with_prefix(prefix)
        
        # Build folder info for each subfolder
        folders = []
        for folder_name in subfolder_names:
            folder_path = f"{prefix}{folder_name}"
            
            # Get item count and total size for this folder
            # This counts all items recursively in the folder
            folder_prefix = f"{folder_path}/"
            all_objects = media_repo.get_all(limit=10000, offset=0, prefix=None)  # Get all to filter
            
            # Filter objects that start with this folder's prefix
            folder_objects = [obj for obj in all_objects if obj.object_key and obj.object_key.startswith(folder_prefix)]
            item_count = len(folder_objects)
            total_size = sum(obj.file_size or 0 for obj in folder_objects)
            
            folders.append(FolderInfo(
                name=folder_name,
                path=folder_path,
                parent_path=path,
                item_count=item_count,
                total_size=total_size
            ))
        
        # Determine parent path for navigation
        parent_path = None
        if path:
            path_parts = path.split('/')
            if len(path_parts) > 1:
                parent_path = '/'.join(path_parts[:-1])
            else:
                parent_path = None  # Parent of top-level folder is root
        
        return FoldersResponse(
            folders=folders,
            current_path=path,
            parent_path=parent_path
        )
        
    except Exception as e:
        logger.error(f"Error getting library folders at path {path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get folders: {str(e)}"
        )


@router.get("/media/by-folder/{path:path}", response_model=MediaByFolderResponse)
@router.get("/media/by-folder", response_model=MediaByFolderResponse, include_in_schema=False)
async def get_library_media_by_folder(
    path: Optional[str] = None,
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_user),
):
    """Get media objects in a specific folder (non-recursive).
    
    This endpoint returns only media objects that are direct children of the specified folder,
    not including objects in subfolders. It's optimized for file browser views.
    
    Args:
        path: Folder path to get media from (None or empty for root)
        db: Database session
        
    Returns:
        MediaByFolderResponse with media objects in the folder
    """
    try:
        # Normalize path
        if path == "" or path == "/":
            path = None
            
        logger.info(f"Getting library media objects in folder: {path}")
        
        # Initialize repository
        media_repo = MediaObjectRepository(db)
        
        # Build prefix for query
        prefix = f"{path}/" if path else ""
        
        # Use our new method to get objects with exact prefix
        media_objects = media_repo.get_objects_with_prefix(prefix)
        
        # Convert to Pydantic models
        media_object_responses = [obj.to_pydantic() for obj in media_objects]
        
        logger.info(f"Found {len(media_object_responses)} media objects in library folder: {path}")
        
        return MediaByFolderResponse(
            media_objects=media_object_responses,
            folder_path=path,
            total=len(media_object_responses)
        )
        
    except Exception as e:
        logger.error(f"Error getting library media objects in folder {path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get media objects: {str(e)}"
        )