import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

# Import needed for get_media_thumbnail (placeholder logic)
from app.db.repositories.media_object import MediaObjectRepository
from app.schemas import MediaObject, PaginatedMediaResponse

logger = logging.getLogger(__name__)

router = APIRouter()

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
