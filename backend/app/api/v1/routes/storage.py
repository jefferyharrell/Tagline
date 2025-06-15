"""
Storage browsing routes for Tagline backend.

This module provides API endpoints for:
- Browsing storage folders and files
- Triggering background ingestion for discovered media files
"""

import os
from datetime import datetime
from typing import List, Optional

import redis
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from rq import Queue
from sqlalchemy.orm import Session

from app import auth_schemas as schemas
from app.auth_utils import get_current_user
from app.db.database import get_db
from app.db.repositories.media_object import MediaObjectRepository

# Import processor modules to trigger registration via decorators
# The noqa comment prevents linters from flagging unused import, which is needed here.
from app.media_processing import heicprocessor  # noqa: F401
from app.media_processing import jpegprocessor  # noqa: F401
from app.media_processing import pngprocessor  # noqa: F401
from app.media_processing.factory import is_extension_supported
from app.redis_events import publish_queued_event
from app.schemas import MediaObject
from app.storage_provider import get_storage_provider
from app.storage_providers.base import StorageProviderBase
from app.structlog_config import get_logger
from app.tasks.ingest import ingest

logger = get_logger(__name__)

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


class IngestRequest(BaseModel):
    """Request model for ingest operation."""

    path: str = ""
    preserve_metadata: bool = False
    force_regenerate: bool = False


class IngestResponse(BaseModel):
    """Response model for ingest operation."""

    success: bool
    message: str
    queued_count: int


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

        logger.info(
            "Getting folders at path",
            operation="api_request",
            endpoint="get_folders",
            path=path
        )

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
            all_objects = media_repo.get_all(
                limit=10000, offset=0, prefix=None
            )  # Get all to filter

            # Filter objects that start with this folder's prefix
            folder_objects = [
                obj
                for obj in all_objects
                if obj.object_key and obj.object_key.startswith(folder_prefix)
            ]
            item_count = len(folder_objects)
            total_size = sum(obj.file_size or 0 for obj in folder_objects)

            folders.append(
                FolderInfo(
                    name=folder_name,
                    path=folder_path,
                    parent_path=path,
                    item_count=item_count,
                    total_size=total_size,
                )
            )

        # Determine parent path for navigation
        parent_path = None
        if path:
            path_parts = path.split("/")
            if len(path_parts) > 1:
                parent_path = "/".join(path_parts[:-1])
            else:
                parent_path = None  # Parent of top-level folder is root

        return FoldersResponse(
            folders=folders, current_path=path, parent_path=parent_path
        )

    except Exception as e:
        logger.error(
            "Error getting folders at path",
            operation="get_folders",
            path=path,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get folders: {str(e)}",
        )


@router.get("/media/by-folder/{path:path}", response_model=MediaByFolderResponse)
@router.get(
    "/media/by-folder", response_model=MediaByFolderResponse, include_in_schema=False
)
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

        logger.info(
            "Getting media objects in folder",
            operation="api_request",
            endpoint="get_media_by_folder",
            path=path
        )

        # Initialize repository
        media_repo = MediaObjectRepository(db)

        # Build prefix for query
        prefix = f"{path}/" if path else ""

        # Use our new method to get objects with exact prefix
        media_objects = media_repo.get_objects_with_prefix(prefix)

        # Convert to Pydantic models
        media_object_responses = [obj.to_pydantic() for obj in media_objects]

        logger.info(
            "Found media objects in folder",
            operation="get_media_by_folder",
            path=path,
            media_objects_count=len(media_object_responses)
        )

        return MediaByFolderResponse(
            media_objects=media_object_responses,
            folder_path=path,
            total=len(media_object_responses),
        )

    except Exception as e:
        logger.error(
            "Error getting media objects in folder",
            operation="get_media_by_folder",
            path=path,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get media objects: {str(e)}",
        )


@router.post("/ingest", response_model=IngestResponse)
async def trigger_ingest(
    request: IngestRequest,
    storage_provider: StorageProviderBase = Depends(get_storage_provider),
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_user),
):
    """Trigger manual ingest operation for a specific path.

    This endpoint can be used to:
    - Re-ingest files with thumbnail/proxy regeneration
    - Preserve existing metadata while regenerating media derivatives
    - Force processing of previously processed files

    Args:
        request: Ingest configuration including path and options
        storage_provider: Storage provider instance
        db: Database session

    Returns:
        IngestResponse with operation result and queue count
    """
    try:
        logger.info(
            "Manual ingest requested",
            operation="trigger_ingest",
            path=request.path,
            preserve_metadata=request.preserve_metadata,
            force_regenerate=request.force_regenerate
        )

        # Initialize repository and Redis for queueing
        media_repo = MediaObjectRepository(db)
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        redis_conn = redis.from_url(redis_url)
        ingest_queue = Queue("ingest", connection=redis_conn)

        # Get directory listing from storage provider
        items = storage_provider.list_directory(
            prefix=request.path if request.path else None
        )

        # Filter to only files (not folders)
        files = [item for item in items if not item.is_folder]

        # Process discovered files: create MediaObjects and queue ingest tasks
        newly_queued = 0
        requeued_count = 0

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
                    file_last_modified = datetime.fromisoformat(
                        file_item.last_modified.replace("Z", "+00:00")
                    )
                except ValueError:
                    logger.warning(
                        "Could not parse last_modified timestamp",
                        operation="trigger_ingest",
                        object_key=file_item.object_key,
                        last_modified=file_item.last_modified,
                        error_type="timestamp_parse_error"
                    )

            # Handle existing vs new objects based on preserve_metadata flag
            if request.preserve_metadata:
                # Check if object already exists
                existing_obj = media_repo.get_by_object_key(file_item.object_key)
                if existing_obj:
                    # Object exists - only queue if force_regenerate is True
                    if request.force_regenerate:
                        try:
                            job = ingest_queue.enqueue(ingest, file_item.object_key)
                            logger.info(
                                "Requeued existing object for regeneration",
                                operation="trigger_ingest",
                                object_key=file_item.object_key,
                                job_id=job.id
                            )
                            requeued_count += 1

                            # Publish queued event
                            media_obj_pydantic = existing_obj.to_pydantic()
                            publish_queued_event(media_obj_pydantic)

                        except Exception as e:
                            logger.error(
                                "Failed to requeue ingest job",
                                operation="trigger_ingest",
                                object_key=file_item.object_key,
                                error=str(e),
                                error_type=type(e).__name__
                            )
                    continue
                else:
                    # New object - create it and queue for processing
                    media_obj, was_created = media_repo.create_sparse(
                        object_key=file_item.object_key,
                        file_size=file_item.size,
                        file_mimetype=file_item.mimetype,
                        file_last_modified=file_last_modified,
                    )
            else:
                # Not preserving metadata - create/update object normally
                media_obj, was_created = media_repo.create_sparse(
                    object_key=file_item.object_key,
                    file_size=file_item.size,
                    file_mimetype=file_item.mimetype,
                    file_last_modified=file_last_modified,
                )

            # Queue for ingestion if we created the object or force_regenerate is True
            should_queue = (media_obj and was_created) or (
                request.force_regenerate and media_obj
            )

            if should_queue and media_obj:
                try:
                    job = ingest_queue.enqueue(ingest, file_item.object_key)
                    logger.info(
                        "Queued ingest job for file",
                        operation="trigger_ingest",
                        object_key=file_item.object_key,
                        job_id=job.id
                    )
                    newly_queued += 1

                    # Publish queued event with MediaObject data
                    media_obj_pydantic = media_obj.to_pydantic()
                    publish_queued_event(media_obj_pydantic)
                    logger.debug(
                        "Published queued event",
                        operation="trigger_ingest",
                        object_key=media_obj.object_key
                    )

                except Exception as e:
                    logger.error(
                        "Failed to queue ingest job",
                        operation="trigger_ingest",
                        object_key=file_item.object_key,
                        error=str(e),
                        error_type=type(e).__name__
                    )

        total_queued = newly_queued + requeued_count

        if total_queued > 0:
            logger.info(
                "Manual ingest completed",
                operation="trigger_ingest",
                newly_queued=newly_queued,
                requeued_count=requeued_count,
                total_queued=total_queued
            )
            message = f"Queued {total_queued} files for processing"
            if request.preserve_metadata:
                message += " (preserving metadata)"
            if request.force_regenerate:
                message += " (forcing regeneration)"
        else:
            message = "No files found to process"

        return IngestResponse(success=True, message=message, queued_count=total_queued)

    except Exception as e:
        logger.error(
            "Error during manual ingest",
            operation="trigger_ingest",
            path=request.path,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger ingest: {str(e)}",
        )
