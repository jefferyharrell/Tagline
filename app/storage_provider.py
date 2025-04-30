from typing import Optional, Protocol


class StorageProviderBase(Protocol):
    """
    Protocol for storage providers.
    All storage backends (local, S3, etc.) must implement this interface.
    """

    async def list(
        self, prefix: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> list[str]:
        """
        List media objects in storage.

        Args:
            prefix: Optional path/namespace prefix
            limit: Maximum number of objects to return
            offset: Number of objects to skip
        Returns:
            A list of media object keys
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
