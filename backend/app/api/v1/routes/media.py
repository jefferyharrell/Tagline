import logging
from typing import List, cast
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Import needed for get_media_thumbnail (placeholder logic)
from app.db.repositories.media_object import MediaObjectRepository
from app.dependencies import get_media_object_repository, get_s3_binary_storage
from app.schemas import MediaObject, MediaObjectPatch, PaginatedMediaResponse
from app.storage_provider import get_storage_provider

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/media/{object_key:path}/data", response_class=StreamingResponse, tags=["media"]
)
async def get_media_data(
    object_key: str,
    repo: MediaObjectRepository = Depends(get_media_object_repository),
    provider=Depends(get_storage_provider),
) -> StreamingResponse:
    """Returns the raw bytes of a media object by object_key as a streamable response.

    Returns 404 if not found.
    """
    # URL decode the object_key
    object_key = unquote(object_key)

    # Get the media object record
    record = repo.get_by_object_key(object_key)
    if not record or not record.object_key:
        raise HTTPException(status_code=404, detail="Media object not found")

    # provider is now injected by FastAPI
    # Get the mimetype from metadata or default to octet-stream
    mimetype = record.metadata.get("mimetype", "application/octet-stream")

    # Create an async generator to stream the bytes
    async def content_stream():
        try:
            # At this point we know object_key is not None due to the check above
            object_key = cast(
                str, record.object_key
            )  # Type assertion since we checked above
            for chunk in provider.iter_object_bytes(object_key):
                yield chunk
        except FileNotFoundError:
            # If the file is missing from storage but exists in DB
            raise HTTPException(
                status_code=404,
                detail="Media object content not found in storage",
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve media object content: {str(e)}",
            )

    return StreamingResponse(
        content=content_stream(),
        media_type=mimetype,
        headers={
            "Content-Disposition": f'attachment; filename="{record.object_key.split("/")[-1]}"'
        },
    )


# --- Pydantic Models ---


class PaginatedMediaObjectList(BaseModel):
    """Response model for paginated list of media objects."""

    items: List[MediaObject]
    total: int = Field(..., description="Total number of items available.")
    limit: int = Field(..., description="Number of items per page (page size).")
    offset: int = Field(..., description="Offset for pagination.")
    pages: int = Field(..., description="Total number of pages.")


# --- Endpoints ---


@router.get(
    "/media",
    response_model=PaginatedMediaResponse,
    summary="Get Media Objects List",
    tags=["media"],
)
def list_media_objects(
    limit: int = Query(100, ge=1, le=500, description="Number of items per page."),
    offset: int = Query(0, ge=0, description="Pagination offset."),
    prefix: str = Query(None, description="Filter objects by object_key prefix."),
    repo: MediaObjectRepository = Depends(get_media_object_repository),
) -> PaginatedMediaResponse:
    """
    Retrieves a paginated list of media objects stored in the database.
    Optionally filtered by object_key prefix (e.g., "/2024/Spring Gala/").
    """
    total_count = repo.count(prefix=prefix)
    media_records = repo.get_all(limit=limit, offset=offset, prefix=prefix)

    # Convert to API schema
    media_objects = [record.to_pydantic() for record in media_records]

    # Note: The total_count might slightly differ from len(media_objects) if filtering occurred.
    # This is generally acceptable for pagination display but could be refined if needed.
    # Calculate pages
    pages = (total_count + limit - 1) // limit if limit > 0 else 0

    return PaginatedMediaResponse(
        items=media_objects, total=total_count, limit=limit, offset=offset, pages=pages
    )


# Route moved to end of file to avoid path parameter conflicts


@router.patch("/media/{object_key:path}", response_model=MediaObject, tags=["media"])
def patch_media_object(
    object_key: str,
    patch_request: MediaObjectPatch,
    repo: MediaObjectRepository = Depends(get_media_object_repository),
) -> MediaObject:
    """
    Partially update metadata for a media object by its object_key.
    Merges new fields into the existing metadata dict. Returns the updated object.
    """
    # URL decode the object_key
    object_key = unquote(object_key)

    record = repo.get_by_object_key(object_key)
    if not record or not record.object_key:
        raise HTTPException(status_code=404, detail="Media object not found")

    # Extract metadata from the patch request
    patch_dict = patch_request.model_dump(exclude_unset=True)
    if not patch_dict or "metadata" not in patch_dict:
        # No metadata changes requested, return current object
        return record.to_pydantic()

    # Defensive: ensure record.metadata is a dict
    existing_metadata = record.metadata or {}
    new_metadata = patch_dict["metadata"]

    # Merge new metadata into existing metadata
    merged_metadata = {**existing_metadata, **new_metadata}

    # Save using update_metadata method
    try:
        success = repo.update_metadata(object_key, merged_metadata)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update media object")

        # Retrieve updated record
        updated = repo.get_by_object_key(object_key)
        if not updated:
            raise HTTPException(
                status_code=404, detail="Media object not found after update"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update media object: {e}"
        )
    return updated.to_pydantic()


@router.get(
    "/media/{object_key:path}/thumbnail",
    response_class=StreamingResponse,
    tags=["media"],
)
def get_media_thumbnail(
    object_key: str,
    repo: MediaObjectRepository = Depends(get_media_object_repository),
    s3_storage=Depends(get_s3_binary_storage),
):
    """
    Returns the thumbnail bytes for a media object by object_key, or 404 if not found or no thumbnail exists.
    Streams from S3 if available.
    """
    # URL decode the object_key
    original_object_key = object_key
    object_key = unquote(object_key)
    logger.info(
        f"Getting thumbnail for original='{original_object_key}' decoded='{object_key}'"
    )

    media_object = repo.get_by_object_key(object_key)
    if not media_object:
        # Debug: check what objects exist in the database
        all_objects = repo.get_all(limit=10, offset=0)
        object_keys = [obj.object_key for obj in all_objects if obj.object_key]
        raise HTTPException(
            status_code=404,
            detail=f"Media object not found for key: '{object_key}'. Available keys: {object_keys}",
        )

    logger.info(f"Found media object, checking thumbnail metadata for: {object_key}")
    # Get metadata to determine content type
    try:
        metadata = s3_storage.get_thumbnail_metadata(object_key)
        if not metadata:
            logger.warning(f"Thumbnail metadata not found for: {object_key}")
            raise HTTPException(status_code=404, detail="Thumbnail not found")

        logger.info(f"Thumbnail metadata found, streaming for: {object_key}")
        # Stream from S3
        stream = s3_storage.stream_thumbnail(object_key)
        return StreamingResponse(
            content=stream,
            media_type=metadata.get("content_type", "image/jpeg"),
            headers={
                "Cache-Control": "public, max-age=3600",
                "ETag": metadata.get("etag", ""),
            },
        )
    except FileNotFoundError:
        logger.warning(f"Thumbnail file not found in S3 for: {object_key}")
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    except Exception as e:
        logger.error(f"Error streaming thumbnail from S3 for {object_key}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving thumbnail")


@router.get(
    "/media/{object_key:path}/proxy", response_class=StreamingResponse, tags=["media"]
)
def get_media_proxy(
    object_key: str,
    repo: MediaObjectRepository = Depends(get_media_object_repository),
    s3_storage=Depends(get_s3_binary_storage),
):
    """
    Returns the proxy bytes for a media object by object_key, or 404 if not found or no proxy exists.
    Streams from S3 if available.
    """
    # URL decode the object_key
    object_key = unquote(object_key)

    media_object = repo.get_by_object_key(object_key)
    if not media_object:
        raise HTTPException(status_code=404, detail="Media object not found")

    # Get metadata to determine content type
    try:
        metadata = s3_storage.get_proxy_metadata(object_key)
        if not metadata:
            raise HTTPException(status_code=404, detail="Proxy not found")

        # Stream from S3
        stream = s3_storage.stream_proxy(object_key)
        return StreamingResponse(
            content=stream,
            media_type=metadata.get("content_type", "image/jpeg"),
            headers={
                "Cache-Control": "public, max-age=3600",
                "ETag": metadata.get("etag", ""),
            },
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Proxy not found")
    except Exception as e:
        logger.error(f"Error streaming proxy from S3 for {object_key}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving proxy")


class AdjacentMediaResponse(BaseModel):
    """Response model for adjacent media objects."""

    previous: MediaObject | None = None
    next: MediaObject | None = None


@router.get("/media/debug-sparkle", tags=["media"])
def debug_sparkle_specifically(
    repo: MediaObjectRepository = Depends(get_media_object_repository),
):
    """Debug endpoint to check if _Sparkle.heic exists."""
    all_objects = repo.get_all(limit=10, offset=0)
    object_keys = [obj.object_key for obj in all_objects if obj.object_key]
    sparkle_exists = repo.get_by_object_key("_Sparkle.heic")

    return {
        "available_keys": object_keys,
        "sparkle_exists": sparkle_exists is not None,
        "sparkle_object": sparkle_exists.to_pydantic() if sparkle_exists else None,
    }


@router.get("/media/{object_key:path}/debug", tags=["media"])
def debug_media_object(
    object_key: str,
    repo: MediaObjectRepository = Depends(get_media_object_repository),
):
    """Debug endpoint to check object key processing."""
    from urllib.parse import unquote

    original_object_key = object_key
    object_key = unquote(object_key)

    all_objects = repo.get_all(limit=10, offset=0)
    object_keys = [obj.object_key for obj in all_objects if obj.object_key]

    return {
        "original_object_key": original_object_key,
        "decoded_object_key": object_key,
        "available_keys": object_keys,
        "key_exists": any(key == object_key for key in object_keys),
    }


@router.get(
    "/media/{object_key:path}/adjacent",
    response_model=AdjacentMediaResponse,
    tags=["media"],
)
def get_adjacent_media(
    object_key: str, repo: MediaObjectRepository = Depends(get_media_object_repository)
) -> AdjacentMediaResponse:
    """
    Get the previous and next media objects relative to the given media object.
    Used for implementing photo navigation without returning to the gallery.
    """
    # URL decode the object_key
    object_key = unquote(object_key)

    # First, verify the current media object exists
    current = repo.get_by_object_key(object_key)
    if not current or not current.object_key:
        raise HTTPException(status_code=404, detail="Media object not found")

    # Get adjacent media objects
    previous_obj, next_obj = repo.get_adjacent(object_key)

    # Convert to pydantic models if they exist
    previous = previous_obj.to_pydantic() if previous_obj else None
    next = next_obj.to_pydantic() if next_obj else None

    return AdjacentMediaResponse(previous=previous, next=next)


# This route must be last to avoid conflicting with more specific routes above
@router.get("/media/{object_key:path}", response_model=MediaObject, tags=["media"])
def get_media_object(
    object_key: str, repo: MediaObjectRepository = Depends(get_media_object_repository)
) -> MediaObject:
    """
    Retrieve a single media object by its object_key.
    Returns 404 if not found.
    """
    # URL decode the object_key
    object_key = unquote(object_key)

    record = repo.get_by_object_key(object_key)
    if not record or not record.object_key:
        raise HTTPException(status_code=404, detail="Media object not found")
    return record.to_pydantic()
