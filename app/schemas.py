from typing import List, Optional

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
