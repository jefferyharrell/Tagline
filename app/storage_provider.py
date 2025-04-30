from typing import List, Optional, Protocol

from pydantic import BaseModel


class MediaObject(BaseModel):
    object_key: str
    last_modified: Optional[str] = None  # or datetime
    metadata: Optional[dict] = None


class StorageProviderBase(Protocol):
    """
    Protocol for storage providers.
    All storage backends (local, S3, etc.) must implement this interface.
    """

    async def list(
        self,
        prefix: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        regex: Optional[str] = None,
    ) -> List[MediaObject]:
        """
        List media objects in storage, optionally filtered by regex on object key.

        Args:
            prefix: Only return keys with this prefix.
            limit: Max number of results.
            offset: Start at this offset.
            regex: If provided, only return keys matching this regex pattern.

        Returns:
            List of MediaObject objects. If the provider can supply metadata (e.g., width, height, last_modified) as part of the listing, the MediaObject.metadata property SHOULD be set; otherwise, it MAY be empty or omitted.
        """
        ...

    async def retrieve(self, object_key: str) -> bytes:
        """
        Retrieve a media object's raw data from storage.

        Args:
            object_key: Unique identifier for the object
        Returns:
            The raw bytes of the object
        """
        ...
