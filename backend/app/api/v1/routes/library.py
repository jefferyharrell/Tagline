"""
Library browsing routes for Tagline backend.

This module provides API endpoints for:
- Browsing the media library folder structure
- Getting media objects in specific folders
- Folder navigation and hierarchy
"""

import asyncio
import json
import os
import time
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


def get_cache_key(path: Optional[str]) -> str:
    """Generate Redis cache key for directory listing."""
    return f"dropbox_list:{path or 'root'}"


def cache_directory_listing(
    redis_conn: redis.Redis, path: Optional[str], items: List, ttl: int = 86400 * 30
):
    """Cache directory listing in Redis."""
    cache_key = get_cache_key(path)
    # Convert items to dict format for JSON serialization
    items_data = [
        {
            "name": item.name,
            "is_folder": item.is_folder,
            "object_key": item.object_key,
            "size": item.size,
            "last_modified": item.last_modified,
            "mimetype": item.mimetype,
        }
        for item in items
    ]
    redis_conn.setex(cache_key, ttl, json.dumps(items_data))
    logger.debug(
        "Directory listing cached",
        operation="cache_set",
        path=path,
        items_count=len(items),
        ttl=ttl
    )


def get_cached_directory_listing(redis_conn: redis.Redis, path: Optional[str]):
    """Get cached directory listing from Redis."""
    cache_key = get_cache_key(path)
    cached_data = redis_conn.get(cache_key)
    if cached_data:
        try:
            items_data = json.loads(cached_data)
            logger.debug(
                "Using cached directory listing",
                operation="cache_get",
                path=path,
                items_count=len(items_data)
            )
            # Convert back to DirectoryItem objects
            return [
                DirectoryItem(
                    name=item["name"],
                    is_folder=item["is_folder"],
                    object_key=item["object_key"],
                    size=item["size"],
                    last_modified=item["last_modified"],
                    mimetype=item["mimetype"],
                )
                for item in items_data
            ]
        except json.JSONDecodeError:
            logger.warning(
                "Failed to decode cached data",
                operation="cache_get",
                path=path,
                error_type="json_decode_error"
            )
            redis_conn.delete(cache_key)
    return None


async def prefetch_subfolders_async(
    storage_provider, redis_conn: redis.Redis, folders: List, ttl: int = 86400 * 30
):
    """Asynchronously prefetch and cache first-level subfolders."""
    import concurrent.futures

    def prefetch_folder_sync(folder_object_key: str) -> bool:
        """Synchronous function to prefetch a single folder."""
        try:
            # Check if already cached
            if not get_cached_directory_listing(redis_conn, folder_object_key):
                # Fetch and cache this subfolder
                subfolder_items = storage_provider.list_directory(
                    prefix=folder_object_key
                )
                cache_directory_listing(
                    redis_conn, folder_object_key, subfolder_items, ttl
                )
                logger.info(
                    "Subfolder prefetched and cached",
                    operation="prefetch_folder",
                    folder_object_key=folder_object_key,
                    items_count=len(subfolder_items)
                )
                return True
            else:
                logger.debug(
                    "Subfolder already cached",
                    operation="prefetch_folder",
                    folder_object_key=folder_object_key,
                    status="cached"
                )
                return False
        except Exception as e:
            logger.warning(
                "Failed to prefetch subfolder",
                operation="prefetch_folder",
                folder_object_key=folder_object_key,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    # Use thread pool executor to run synchronous operations
    loop = asyncio.get_event_loop()

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Create tasks for all subfolders (limit to first 5)
        folder_keys = [folder.object_key for folder in folders[:5] if folder.object_key]

        if folder_keys:
            logger.info(
                "Starting background prefetch",
                operation="prefetch_subfolders",
                subfolder_count=len(folder_keys)
            )
            try:
                # Run sync operations in thread pool
                tasks = [
                    loop.run_in_executor(executor, prefetch_folder_sync, folder_key)
                    for folder_key in folder_keys
                ]

                # Wait for all tasks to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Count successful prefetches
                successful = sum(1 for result in results if result is True)
                logger.info(
                    "Background prefetch completed",
                    operation="prefetch_subfolders",
                    successful_count=successful,
                    total_count=len(folder_keys)
                )

            except Exception as e:
                logger.warning(
                    "Error in background prefetch",
                    operation="prefetch_subfolders",
                    error=str(e),
                    error_type=type(e).__name__
                )


class DirectoryItem:
    """Simple directory item class for caching."""

    def __init__(
        self,
        name: str,
        is_folder: bool,
        object_key: Optional[str] = None,
        size: Optional[int] = None,
        last_modified: Optional[str] = None,
        mimetype: Optional[str] = None,
    ):
        self.name = name
        self.is_folder = is_folder
        self.object_key = object_key
        self.size = size
        self.last_modified = last_modified
        self.mimetype = mimetype


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
    refresh: bool = False,
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
        refresh: If True, bypass cache and refresh from storage provider
        storage_provider: Storage provider instance
        db: Database session

    Returns:
        BrowseResponse with folders and paginated MediaObjects
    """
    import time

    start_time = time.time()

    try:
        logger.info(
            "Browsing library path",
            operation="api_request",
            endpoint="browse_library",
            path=path,
            limit=limit,
            offset=offset
        )

        # Initialize repository and Redis for queueing
        media_repo = MediaObjectRepository(db)
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        redis_conn = redis.from_url(redis_url)
        ingest_queue = Queue("ingest", connection=redis_conn)

        # Try to get directory listing from cache first (unless refresh is requested)
        cached_items = (
            None if refresh else get_cached_directory_listing(redis_conn, path)
        )

        if cached_items:
            items = cached_items
            logger.info(
                "Using cached directory listing",
                operation="browse_library",
                cache_status="hit",
                path=path,
                items_count=len(items)
            )
        else:
            # Clear cache if refresh was requested
            if refresh:
                cache_key = get_cache_key(path)
                redis_conn.delete(cache_key)
                logger.info(
                    "Cache cleared due to refresh request",
                    operation="browse_library",
                    path=path,
                    refresh=True
                )

            # Get directory listing from storage provider and cache it
            items = storage_provider.list_directory(prefix=path)
            # Use longer TTL for archived content (30 days)
            cache_directory_listing(redis_conn, path, items, ttl=86400 * 30)
            logger.info(
                "Directory listing fetched and cached",
                operation="browse_library",
                cache_status="miss",
                path=path,
                items_count=len(items)
            )

        # Separate folders and files
        separation_start = time.time()
        folders = [item for item in items if item.is_folder]
        files = [item for item in items if not item.is_folder]
        separation_time = time.time() - separation_start
        logger.info(
            "Folder/file separation completed",
            operation="browse_library",
            phase="separation",
            duration_ms=separation_time * 1000,
            total_items=len(items),
            folders_count=len(folders),
            files_count=len(files)
        )

        # Process discovered files: create MediaObjects and queue ingest tasks
        # Only process files if we got a fresh directory listing (not cached)
        processing_start = time.time()
        newly_queued = 0
        if cached_items is None:  # Only process files when fetching fresh data
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
                            operation="browse_library",
                            phase="file_processing",
                            object_key=file_item.object_key,
                            last_modified=file_item.last_modified,
                            error_type="datetime_parse_error"
                        )

                # Create sparse MediaObject record (with ON CONFLICT DO NOTHING behavior)
                media_obj, was_created = media_repo.create_sparse(
                    object_key=file_item.object_key,
                    file_size=file_item.size,
                    file_mimetype=file_item.mimetype,
                    file_last_modified=file_last_modified,
                )

                # Only queue for ingestion if we actually created the object
                if media_obj and was_created:
                    try:
                        job = ingest_queue.enqueue(ingest, media_obj.object_key)
                        logger.info(
                            "Ingest job queued for newly discovered file",
                            operation="browse_library",
                            phase="file_processing",
                            job_id=job.id,
                            object_key=file_item.object_key
                        )
                        newly_queued += 1

                        # Publish queued event with MediaObject data
                        media_obj_pydantic = media_obj.to_pydantic()
                        publish_queued_event(media_obj_pydantic)
                        logger.debug(
                            "Published queued event",
                            operation="browse_library",
                            phase="file_processing",
                            object_key=media_obj.object_key
                        )

                    except Exception as e:
                        logger.error(
                            "Failed to queue ingest job",
                            operation="browse_library",
                            phase="file_processing",
                            object_key=file_item.object_key,
                            error=str(e),
                            error_type=type(e).__name__
                        )

        processing_time = time.time() - processing_start
        logger.info(
            "File processing completed",
            operation="browse_library",
            phase="file_processing",
            duration_ms=processing_time * 1000,
            files_count=len(files),
            newly_queued=newly_queued
        )

        if newly_queued > 0:
            logger.info(
                "New files queued for ingestion",
                operation="browse_library",
                phase="file_processing",
                newly_queued=newly_queued
            )

        # Now get all MediaObjects for this path with pagination
        # Build the prefix for exact folder matching
        # For root level, we pass None to get a special handling in the repository
        prefix_filter = f"{path}/" if path else None

        # If refresh was requested, sync database with current Dropbox state
        if refresh:
            logger.info(
                "Starting database sync for refresh",
                operation="browse_library",
                phase="refresh_sync",
                path=path
            )

            # Get current media objects in database for this path
            existing_media_objects = media_repo.get_all(
                limit=10000, offset=0, prefix=prefix_filter
            )
            existing_object_keys = {obj.object_key for obj in existing_media_objects}
            logger.info(
                "Found existing media objects in database",
                operation="browse_library",
                phase="refresh_sync",
                existing_count=len(existing_object_keys)
            )
            logger.debug(
                "Existing object keys",
                operation="browse_library",
                phase="refresh_sync",
                existing_keys=list(existing_object_keys)
            )

            # Get current files from Dropbox (already fetched above)
            current_file_keys = {
                file_item.object_key for file_item in files if file_item.object_key
            }
            logger.info(
                "Found current files in storage",
                operation="browse_library",
                phase="refresh_sync",
                current_files_count=len(current_file_keys)
            )
            logger.debug(
                "Current storage file keys",
                operation="browse_library",
                phase="refresh_sync",
                current_keys=list(current_file_keys)
            )

            # Find media objects that exist in database but not in Dropbox (deleted files)
            deleted_keys = existing_object_keys - current_file_keys
            logger.info(
                "Keys identified for deletion",
                operation="browse_library",
                phase="refresh_sync",
                deleted_keys=list(deleted_keys),
                deleted_count=len(deleted_keys)
            )

            if deleted_keys:
                logger.info(
                    "Removing deleted media objects from database",
                    operation="browse_library",
                    phase="refresh_sync",
                    deleted_count=len(deleted_keys)
                )
                for deleted_key in deleted_keys:
                    try:
                        success = media_repo.delete_by_object_key(deleted_key)
                        logger.info(
                            "Media object deletion result",
                            operation="browse_library",
                            phase="refresh_sync",
                            deleted_key=deleted_key,
                            success=success
                        )
                    except Exception as e:
                        logger.error(
                            "Failed to delete media object",
                            operation="browse_library",
                            phase="refresh_sync",
                            deleted_key=deleted_key,
                            error=str(e),
                            error_type=type(e).__name__
                        )
            else:
                logger.info(
                    "No media objects to delete",
                    operation="browse_library",
                    phase="refresh_sync"
                )

        # Get paginated MediaObjects
        query_start = time.time()
        media_objects = media_repo.get_all(
            limit=limit, offset=offset, prefix=prefix_filter
        )
        query_time = time.time() - query_start
        logger.info(
            "Media objects query completed",
            operation="browse_library",
            phase="query",
            duration_ms=query_time * 1000,
            returned_objects=len(media_objects)
        )

        # Get total count for pagination
        count_start = time.time()
        total_count = media_repo.count(prefix=prefix_filter)
        count_time = time.time() - count_start
        logger.info(
            "Count query completed",
            operation="browse_library",
            phase="count",
            duration_ms=count_time * 1000,
            total_count=total_count
        )

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
        pydantic_start = time.time()
        media_object_responses = [obj.to_pydantic() for obj in media_objects]
        pydantic_time = time.time() - pydantic_start
        logger.info(
            "Pydantic conversion completed",
            operation="browse_library",
            phase="conversion",
            duration_ms=pydantic_time * 1000,
            objects_count=len(media_objects)
        )

        end_time = time.time()
        logger.info(
            "Browse operation completed",
            operation="browse_library",
            phase="complete",
            total_duration_ms=(end_time - start_time) * 1000,
            folders_count=len(folders),
            media_objects_count=len(media_object_responses)
        )

        # Presumptive caching: If at root level (no path), prefetch first-level subfolders
        prefetch_start = time.time()
        if not path and folders:
            logger.info(
                "Starting presumptive prefetch at root level",
                operation="browse_library",
                phase="prefetch",
                subfolders_count=len(folders)
            )
            # Start background task to prefetch subfolders (don't await)
            asyncio.create_task(
                prefetch_subfolders_async(
                    storage_provider, redis_conn, folders, ttl=86400 * 30
                )
            )
        prefetch_time = time.time() - prefetch_start
        logger.info(
            "Prefetch setup completed",
            operation="browse_library",
            phase="prefetch_setup",
            duration_ms=prefetch_time * 1000
        )

        return BrowseResponse(
            folders=folder_responses,
            media_objects=media_object_responses,
            total=total_count,
            limit=limit,
            offset=offset,
            has_more=(offset + len(media_object_responses)) < total_count,
        )

    except Exception as e:
        logger.error(
            "Error browsing library path",
            operation="browse_library",
            path=path,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to browse library: {str(e)}",
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

        logger.info(
            "Getting library folders",
            operation="api_request",
            endpoint="get_library_folders",
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
            "Error getting library folders",
            operation="get_library_folders",
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

        logger.info(
            "Getting library media objects in folder",
            operation="api_request",
            endpoint="get_library_media_by_folder",
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
            "Found media objects in library folder",
            operation="get_library_media_by_folder",
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
            "Error getting library media objects in folder",
            operation="get_library_media_by_folder",
            path=path,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get media objects: {str(e)}",
        )
