import math
import random
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

# Import needed for get_media_thumbnail (placeholder logic)
from app.db.repositories.media_object import MediaObjectRepository
from app.storage_provider import get_storage_provider
from app.storage_providers.base import StorageProviderBase

# Use MediaObject from storage_types for consistency with storage provider
from app.storage_types import MediaObject

router = APIRouter()

# --- Pydantic Models ---


class PaginatedMediaObjectList(BaseModel):
    """Response model for paginated list of media objects."""

    items: List[MediaObject]
    total: int = Field(..., description="Total number of items available.")
    limit: int = Field(..., description="Number of items per page (page size).")
    offset: int = Field(..., description="Offset for pagination.")
    pages: int = Field(..., description="Total number of pages.")


# --- Endpoints ---


@router.get("/media", response_model=PaginatedMediaObjectList, tags=["media"])
def list_media_objects(
    limit: int = Query(100, ge=1, le=500, description="Number of items per page."),
    offset: int = Query(0, ge=0, description="Pagination offset."),
    shuffle: Optional[bool] = Query(None, description="Randomize order of items."),
    storage_provider: StorageProviderBase = Depends(get_storage_provider),
):
    """Retrieve a paginated list of media objects."""
    # TODO: Implement count method in concrete storage providers (filesystem.py, dropbox.py)
    # The count method is currently just a placeholder in the protocol.
    total_count = storage_provider.count()  # Assuming no prefix/regex filters for now

    # TODO: Implement efficient shuffling in storage providers or handle here.
    # Current shuffle implementation fetches all items if shuffle=True, which is inefficient.
    if shuffle:
        # Inefficient: fetch all, then shuffle, then slice
        # Consider optimizing in storage provider if possible
        all_items = list(
            storage_provider.all_media_objects()
        )  # Assumes all_media_objects exists and works
        random.shuffle(all_items)
        media_objects = all_items[offset : offset + limit]
        # Adjust total_count if needed, though shuffle usually doesn't change total
        total_count = len(
            all_items
        )  # Recalculate total if all_media_objects filters differently than count()
    else:
        media_objects = storage_provider.list_media_objects(limit=limit, offset=offset)

    total_pages = math.ceil(total_count / limit) if limit > 0 else 0

    return PaginatedMediaObjectList(
        items=media_objects,
        total=total_count,
        limit=limit,
        offset=offset,
        pages=total_pages,
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
