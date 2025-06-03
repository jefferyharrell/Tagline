"""
Storage browsing routes for Tagline backend.

This module provides API endpoints for:
- Browsing storage folders and files
- Triggering background ingestion for discovered media files
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import auth_schemas as schemas
from app.auth_utils import get_current_user
from app.db.database import get_db
from app.db.repositories.media_object import MediaObjectRepository

# Import processor modules to trigger registration via decorators
# The noqa comment prevents linters from flagging unused import, which is needed here.
from app.media_processing import heicprocessor  # noqa: F401
from app.media_processing import jpegprocessor  # noqa: F401
from app.media_processing import pngprocessor   # noqa: F401
from app.schemas import MediaObject

logger = logging.getLogger(__name__)

router = APIRouter()


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



@router.get("/folders/{path:path}", response_model=FoldersResponse)
@router.get("/folders", response_model=FoldersResponse, include_in_schema=False)
async def get_folders(
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
            
        logger.info(f"Getting folders at path: {path}")
        
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
        logger.error(f"Error getting folders at path {path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get folders: {str(e)}"
        )


@router.get("/media/by-folder/{path:path}", response_model=MediaByFolderResponse)
@router.get("/media/by-folder", response_model=MediaByFolderResponse, include_in_schema=False)
async def get_media_by_folder(
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
            
        logger.info(f"Getting media objects in folder: {path}")
        
        # Initialize repository
        media_repo = MediaObjectRepository(db)
        
        # Build prefix for query
        prefix = f"{path}/" if path else ""
        
        # Use our new method to get objects with exact prefix
        media_objects = media_repo.get_objects_with_prefix(prefix)
        
        # Convert to Pydantic models
        media_object_responses = [obj.to_pydantic() for obj in media_objects]
        
        logger.info(f"Found {len(media_object_responses)} media objects in folder: {path}")
        
        return MediaByFolderResponse(
            media_objects=media_object_responses,
            folder_path=path,
            total=len(media_object_responses)
        )
        
    except Exception as e:
        logger.error(f"Error getting media objects in folder {path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get media objects: {str(e)}"
        )