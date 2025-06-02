"""
Storage browsing routes for Tagline backend.

This module provides API endpoints for:
- Browsing storage folders and files
- Triggering background ingestion for discovered media files
"""

import logging
import os
from typing import List, Optional

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
    files: List[DirectoryItemResponse]
    total_folders: int
    total_files: int
    ingestion_queued: int  # Number of files queued for ingestion
    queued_files: List[DirectoryItemResponse]  # List of files that were queued for ingestion


@router.get("/browse", response_model=BrowseResponse)
async def browse_storage(
    path: Optional[str] = None,
    storage_provider: StorageProviderBase = Depends(get_storage_provider),
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_user),
):
    """Browse storage folders and files at the given path.
    
    Also queues ingestion tasks for any media files that aren't already in the database.
    
    Args:
        path: Directory path to browse (None for root)
        storage_provider: Storage provider instance
        db: Database session
        
    Returns:
        BrowseResponse with folders, files, and ingestion info
    """
    try:
        logger.info(f"Browsing storage path: {path}")
        
        # Get directory listing from storage provider
        items = storage_provider.list_directory(prefix=path)
        
        # Separate folders and files
        folders = [item for item in items if item.is_folder]
        files = [item for item in items if not item.is_folder]
        
        # Check which files need ingestion
        media_repo = MediaObjectRepository(db)
        ingestion_queued = 0
        queued_files = []
        
        # Supported media file extensions (add more as needed)
        SUPPORTED_MEDIA_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.mp4', '.mov', '.avi'}
        
        for file_item in files:
            if file_item.object_key:
                # Check if this file is already in the database
                existing_media = media_repo.get_by_object_key(file_item.object_key)
                
                if not existing_media:
                    # Check if it's a supported media file
                    file_ext = file_item.object_key.lower().split('.')[-1] if '.' in file_item.object_key else ''
                    if f'.{file_ext}' in SUPPORTED_MEDIA_EXTENSIONS:
                        # Queue ingestion task using RQ
                        try:
                            logger.info(f"Queueing ingestion for: {file_item.object_key}")
                            
                            # Get Redis connection and queue
                            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
                            redis_conn = redis.from_url(redis_url)
                            ingest_queue = Queue("ingest", connection=redis_conn)
                            
                            # Create a StoredMediaObject for the task
                            from app.schemas import StoredMediaObject
                            stored_media_obj = StoredMediaObject(
                                object_key=file_item.object_key,
                                last_modified=file_item.last_modified,
                                metadata={
                                    "size": file_item.size,
                                    "mimetype": file_item.mimetype,
                                }
                            )
                            
                            # Queue the ingest job
                            ingest_queue.enqueue(
                                "app.tasks.ingest.ingest", 
                                stored_media_object=stored_media_obj
                            )
                            ingestion_queued += 1
                            
                            # Add to queued files list for frontend display
                            queued_files.append(file_item)
                            
                        except Exception as e:
                            logger.error(f"Failed to queue ingestion for {file_item.object_key}: {e}")
        
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
        
        file_responses = [
            DirectoryItemResponse(
                name=file.name,
                is_folder=file.is_folder,
                object_key=file.object_key,
                size=file.size,
                last_modified=file.last_modified,
                mimetype=file.mimetype,
            )
            for file in files
        ]
        
        # Convert queued files to response models
        queued_file_responses = [
            DirectoryItemResponse(
                name=file.name,
                is_folder=file.is_folder,
                object_key=file.object_key,
                size=file.size,
                last_modified=file.last_modified,
                mimetype=file.mimetype,
            )
            for file in queued_files
        ]
        
        logger.info(f"Browse complete: {len(folders)} folders, {len(files)} files, {ingestion_queued} queued for ingestion")
        
        return BrowseResponse(
            folders=folder_responses,
            files=file_responses,
            total_folders=len(folders),
            total_files=len(files),
            ingestion_queued=ingestion_queued,
            queued_files=queued_file_responses,
        )
        
    except Exception as e:
        logger.error(f"Error browsing storage path {path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to browse storage: {str(e)}"
        )