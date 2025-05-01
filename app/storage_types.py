from typing import List, Optional, Protocol

from pydantic import BaseModel


class MediaObject(BaseModel):
    object_key: str
    last_modified: Optional[str] = None  # or datetime
    metadata: Optional[dict] = None


class StorageProviderBase(Protocol):
    provider_name: str

    def list_media_objects(
        self,
        prefix: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        regex: Optional[str] = None,
    ) -> List[MediaObject]: ...

    async def retrieve(self, object_key: str) -> bytes: ...
