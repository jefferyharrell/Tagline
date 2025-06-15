from typing import Iterable, List, Optional, Protocol

from app.schemas import StoredMediaObject


class DirectoryItem:
    """Represents a file or folder in a directory listing."""

    def __init__(
        self,
        name: str,
        is_folder: bool,
        object_key: Optional[str] = None,
        size: Optional[int] = None,
        last_modified: Optional[str] = None,
        mimetype: Optional[str] = None,
    ):
        self.name = name
        self.is_folder = is_folder
        self.object_key = object_key  # Relative path for files, None for folders
        self.size = size
        self.last_modified = last_modified
        self.mimetype = mimetype


class StorageProviderBase(Protocol):
    provider_name: str

    def list_directory(
        self,
        prefix: Optional[str] = None,
    ) -> List[DirectoryItem]:
        """List files and folders at the given prefix path.

        Args:
            prefix: Path prefix to list (None for root directory)

        Returns:
            List of DirectoryItem objects representing files and folders
        """
        ...

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
