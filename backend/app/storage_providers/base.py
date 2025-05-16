from typing import Iterable, List, Optional, Protocol

from app.schemas import StoredMediaObject


class StorageProviderBase(Protocol):
    provider_name: str

    def list_media_objects(
        self,
        prefix: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        regex: Optional[str] = None,
    ) -> List[StoredMediaObject]: ...

    def all_media_objects(
        self,
        prefix: Optional[str] = None,
        regex: Optional[str] = None,
    ) -> Iterable[StoredMediaObject]:
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

    def iter_object_bytes(self, object_key: str) -> Iterable[bytes]:
        """Yield bytes of a single media object in chunks.

        Args:
            object_key: Key of the object to retrieve

        Yields:
            Chunks of bytes from the object

        Raises:
            FileNotFoundError: If the object doesn't exist
            StorageProviderException: For other errors
        """
        ...
