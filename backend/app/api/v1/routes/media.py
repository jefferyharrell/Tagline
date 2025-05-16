import logging
from typing import List, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Import needed for get_media_thumbnail (placeholder logic)
from app.db.repositories.media_object import MediaObjectNotFound, MediaObjectRepository
from app.dependencies import get_media_object_repository
from app.schemas import MediaObject, MediaObjectMetadata, PaginatedMediaResponse
from app.storage_provider import get_storage_provider

logger = logging.getLogger(__name__)

router = APIRouter()


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


# Dependency function for the repository
def get_media_object_repository() -> MediaObjectRepository:
    """Provides an instance of the MediaObjectRepository."""
    return MediaObjectRepository()


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
                )
            )
        else:
            logger.warning(f"Skipping record due to missing id or object_key: {record}")

    # Note: The total_count might slightly differ from len(media_objects) if filtering occurred.
    # This is generally acceptable for pagination display but could be refined if needed.
    return PaginatedMediaResponse(
        items=media_objects, total=total_count, limit=limit, offset=offset
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
    metadata_patch: MediaObjectMetadata,
    repo: MediaObjectRepository = Depends(get_media_object_repository),
) -> MediaObject:
    """
    Partially update metadata for a media object by its UUID.
    Merges new fields into the existing metadata dict. Returns the updated object.
    """
    record = repo.get_by_id(id)
    if not record or record.id is None or record.object_key is None:
        raise HTTPException(status_code=404, detail="Media object not found")

    # Defensive: ensure record.metadata is a dict
    existing_metadata = record.metadata or {}
    patch_dict = metadata_patch.model_dump(exclude_unset=True)
    if not patch_dict:
        # No changes requested, return current object
        return record.to_pydantic()

    # Merge patch into existing metadata
    merged_metadata = {**existing_metadata, **patch_dict}
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


@router.get("/media/{id}/thumbnail", response_class=Response, tags=["media"])
def get_media_thumbnail(id: UUID):
    """
    Returns the thumbnail bytes for a media object by UUID, or 404 if not found or no thumbnail exists.
    Always returns as image/jpeg per API spec.
    """
    repo = MediaObjectRepository()
    media_object = repo.get_by_id(id)
    if not media_object or not getattr(media_object, "thumbnail", None):
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    mimetype = (
        getattr(media_object, "thumbnail_mimetype", None) or "application/octet-stream"
    )
    return Response(content=media_object.thumbnail, media_type=mimetype)


@router.get("/media/{id}/proxy", response_class=Response, tags=["media"])
def get_media_proxy(id: UUID):
    """
    Returns the proxy bytes for a media object by UUID, or 404 if not found or no proxy exists.
    Returns with the stored proxy mimetype, or application/octet-stream if missing.
    """
    repo = MediaObjectRepository()
    media_object = repo.get_by_id(id)
    if not media_object or not getattr(media_object, "proxy", None):
        raise HTTPException(status_code=404, detail="Proxy not found")
    mimetype = (
        getattr(media_object, "proxy_mimetype", None) or "application/octet-stream"
    )
    return Response(content=media_object.proxy, media_type=mimetype)
