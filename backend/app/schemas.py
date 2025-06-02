from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class MediaObjectMetadata(BaseModel):
    description: Optional[str] = Field(
        default=None, max_length=1024, description="Short, human-readable description."
    )
    keywords: Optional[List[str]] = Field(
        default=None, description="List of keywords (each max 64 chars)."
    )

    @field_validator("keywords", mode="before")
    def keyword_length(cls, v):
        if v is not None:
            for kw in v:
                if len(kw) > 64:
                    raise ValueError("Each keyword must be at most 64 characters long.")
        return v


class StoredMediaObject(BaseModel):
    """Schema for media objects as returned by storage providers."""

    object_key: str
    last_modified: Optional[str] = None  # or datetime
    metadata: Optional[dict] = None


class MediaObject(BaseModel):
    """Schema for MediaObject API representation."""

    object_key: str  # Now the primary key
    ingestion_status: str = "pending"
    file_size: Optional[int] = None
    file_mimetype: Optional[str] = None
    file_last_modified: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Optional[dict] = None
    has_thumbnail: bool = False  # Computed field for frontend
    has_proxy: bool = False  # Computed field for frontend


class MediaObjectPatch(BaseModel):
    """Schema for PATCH requests to update media object metadata."""

    metadata: Optional[dict] = Field(
        default=None, description="Metadata to merge into existing metadata."
    )


class PaginatedMediaResponse(BaseModel):
    """Schema for paginated list of MediaObjects."""

    items: List[MediaObject]
    total: int
    limit: int
    offset: int
    pages: int = Field(default=0, description="Total number of pages")
