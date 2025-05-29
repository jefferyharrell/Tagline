import logging
from typing import List, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Import needed for get_media_thumbnail (placeholder logic)
from app.db.repositories.media_object import MediaObjectNotFound, MediaObjectRepository
from app.dependencies import get_media_object_repository, get_s3_binary_storage
from app.schemas import MediaObject, MediaObjectPatch, PaginatedMediaResponse
from app.storage_provider import get_storage_provider

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/media/search", response_model=PaginatedMediaResponse, tags=["media"])
def search_media(
    q: str = Query(..., description="Search query"),
    limit: int = Query(100, ge=1, le=500, description="Items per page"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    repo: MediaObjectRepository = Depends(get_media_object_repository),
) -> PaginatedMediaResponse:
    """
    Search media objects using full-text search.

    The search will tokenize the query and find media objects that contain
    ALL search terms in their searchable fields (description, keywords, filename).

    Example: searching for "red dress" will find items with both "red" AND "dress"
    in any combination across the searchable fields.
    """
    media_records, total_count = repo.search(query=q, limit=limit, offset=offset)

    # Convert to Pydantic models
    media_objects = [record.to_pydantic() for record in media_records]

    # Calculate total pages
    pages = (total_count + limit - 1) // limit if limit > 0 else 0

    return PaginatedMediaResponse(
        items=media_objects,
        total=total_count,
        limit=limit,
        offset=offset,
        pages=pages,
    )


@router.get("/media/{id}/data", response_class=StreamingResponse, tags=["media"])
async def get_media_data(
    id: UUID,
    repo: MediaObjectRepository = Depends(get_media_object_repository),
    provider=Depends(get_storage_provider),
) -> StreamingResponse:
    """Returns the raw bytes of a media object by UUID as a streamable response.

    Returns 404 if not found.
    """
    # Get the media object record
    record = repo.get_by_id(id)
    if not record or record.id is None or not record.object_key:
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
    repo: MediaObjectRepository = Depends(get_media_object_repository),
) -> PaginatedMediaResponse:
    """
    Retrieves a paginated list of media objects stored in the database.
    """
    total_count = repo.count()
    media_records = repo.get_all(limit=limit, offset=offset)

    # Filter records missing essential fields and convert to API schema
    media_objects = []
    for record in media_records:
        if record.id is not None and record.object_key is not None:
            media_objects.append(
                MediaObject(
                    id=record.id,
                    object_key=record.object_key,
                    last_modified=record.last_modified,
                    metadata=record.metadata,
                )
            )
        else:
            logger.warning(f"Skipping record due to missing id or object_key: {record}")

    # Note: The total_count might slightly differ from len(media_objects) if filtering occurred.
    # This is generally acceptable for pagination display but could be refined if needed.
    # Calculate pages
    pages = (total_count + limit - 1) // limit if limit > 0 else 0

    return PaginatedMediaResponse(
        items=media_objects, total=total_count, limit=limit, offset=offset, pages=pages
    )


@router.get("/media/{id}", response_model=MediaObject, tags=["media"])
def get_media_object(
    id: UUID, repo: MediaObjectRepository = Depends(get_media_object_repository)
) -> MediaObject:
    """
    Retrieve a single media object by its UUID.
    Returns 404 if not found.
    """
    record = repo.get_by_id(id)
    if not record or record.id is None or record.object_key is None:
        raise HTTPException(status_code=404, detail="Media object not found")
    return record.to_pydantic()


@router.patch("/media/{id}", response_model=MediaObject, tags=["media"])
def patch_media_object(
    id: UUID,
    patch_request: MediaObjectPatch,
    repo: MediaObjectRepository = Depends(get_media_object_repository),
) -> MediaObject:
    """
    Partially update metadata for a media object by its UUID.
    Merges new fields into the existing metadata dict. Returns the updated object.
    """
    record = repo.get_by_id(id)
    if not record or record.id is None or record.object_key is None:
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
    record.metadata = merged_metadata

    # Update last_modified timestamp
    from datetime import datetime

    record.last_modified = datetime.utcnow().isoformat()

    # Save using explicit save method
    try:
        updated = repo.save(record)
    except MediaObjectNotFound:
        raise HTTPException(status_code=404, detail="Media object not found")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update media object: {e}"
        )
    return updated.to_pydantic()


@router.get("/media/{id}/thumbnail", response_class=StreamingResponse, tags=["media"])
def get_media_thumbnail(
    id: UUID,
    repo: MediaObjectRepository = Depends(get_media_object_repository),
    s3_storage=Depends(get_s3_binary_storage),
):
    """
    Returns the thumbnail bytes for a media object by UUID, or 404 if not found or no thumbnail exists.
    Streams from S3 if available, falls back to database.
    """
    media_object = repo.get_by_id(id)
    if not media_object:
        raise HTTPException(status_code=404, detail="Media object not found")

    # Get metadata to determine content type
    try:
        metadata = s3_storage.get_thumbnail_metadata(str(id))
        if not metadata:
            raise HTTPException(status_code=404, detail="Thumbnail not found")

        # Stream from S3
        stream = s3_storage.stream_thumbnail(str(id))
        return StreamingResponse(
            content=stream,
            media_type=metadata.get("content_type", "image/jpeg"),
            headers={
                "Cache-Control": "public, max-age=3600",
                "ETag": metadata.get("etag", ""),
            },
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    except Exception as e:
        logger.error(f"Error streaming thumbnail from S3 for {id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving thumbnail")


@router.get("/media/{id}/proxy", response_class=StreamingResponse, tags=["media"])
def get_media_proxy(
    id: UUID,
    repo: MediaObjectRepository = Depends(get_media_object_repository),
    s3_storage=Depends(get_s3_binary_storage),
):
    """
    Returns the proxy bytes for a media object by UUID, or 404 if not found or no proxy exists.
    Streams from S3 if available, falls back to database.
    """
    media_object = repo.get_by_id(id)
    if not media_object:
        raise HTTPException(status_code=404, detail="Media object not found")

    # Get metadata to determine content type
    try:
        metadata = s3_storage.get_proxy_metadata(str(id))
        if not metadata:
            raise HTTPException(status_code=404, detail="Proxy not found")

        # Stream from S3
        stream = s3_storage.stream_proxy(str(id))
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
        logger.error(f"Error streaming proxy from S3 for {id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving proxy")


class AdjacentMediaResponse(BaseModel):
    """Response model for adjacent media objects."""

    previous: MediaObject | None = None
    next: MediaObject | None = None


@router.get(
    "/media/{id}/adjacent", response_model=AdjacentMediaResponse, tags=["media"]
)
def get_adjacent_media(
    id: UUID, repo: MediaObjectRepository = Depends(get_media_object_repository)
) -> AdjacentMediaResponse:
    """
    Get the previous and next media objects relative to the given media object.
    Used for implementing photo navigation without returning to the gallery.
    """
    # First, verify the current media object exists
    current = repo.get_by_id(id)
    if not current or current.id is None or current.object_key is None:
        raise HTTPException(status_code=404, detail="Media object not found")

    # Get adjacent media objects
    previous_obj, next_obj = repo.get_adjacent(id)

    # Convert to pydantic models if they exist
    previous = previous_obj.to_pydantic() if previous_obj else None
    next = next_obj.to_pydantic() if next_obj else None

    return AdjacentMediaResponse(previous=previous, next=next)
