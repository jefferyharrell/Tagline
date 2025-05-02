from typing import Optional

from pydantic import BaseModel


class MediaObject(BaseModel):
    object_key: str
    last_modified: Optional[str] = None  # or datetime
    metadata: Optional[dict] = None
