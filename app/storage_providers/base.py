from typing import Iterable, List, Optional, Protocol

from app.storage_types import MediaObject


class StorageProviderBase(Protocol):
    provider_name: str

    def list_media_objects(
        self,
        prefix: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        regex: Optional[str] = None,
    ) -> List[MediaObject]: ...

    def all_media_objects(
        self,
        prefix: Optional[str] = None,
        regex: Optional[str] = None,
    ) -> Iterable[MediaObject]:
        """Return an iterable of all media objects, optionally filtered."""
        ...

    async def retrieve(self, object_key: str) -> bytes: ...

    def count(
        self,
        prefix: Optional[str] = None,
        regex: Optional[str] = None,
    ) -> int:
        """Return the total count of media objects, optionally filtered."""
        ...
