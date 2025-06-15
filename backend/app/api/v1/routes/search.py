"""
Search routes for Tagline backend.

This module provides API endpoints for:
- Full-text search across media metadata
"""

import logging

from fastapi import APIRouter, Depends, Query

from app.db.repositories.media_object import MediaObjectRepository
from app.dependencies import get_media_object_repository
from app.schemas import PaginatedMediaResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=PaginatedMediaResponse, tags=["search"])
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

    # Convert to Pydantic models (filter out any without object_key)
    media_objects = [
        record.to_pydantic()
        for record in media_records
        if record.object_key is not None
    ]

    # Calculate total pages
    pages = (total_count + limit - 1) // limit if limit > 0 else 0

    return PaginatedMediaResponse(
        items=media_objects,
        total=total_count,
        limit=limit,
        offset=offset,
        pages=pages,
    )
