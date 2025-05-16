import mimetypes
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

from app.schemas import StoredMediaObject
from app.storage_providers.base import StorageProviderBase


class FilesystemStorageProvider(StorageProviderBase):
    """
    Storage provider that lists and retrieves files from a local filesystem root.
    The root path is set by the FILESYSTEM_ROOT_PATH environment variable.
    Object keys are relative paths from the root, starting with a slash.
    """

    provider_name: str = "Filesystem"

    def __init__(self, root_path: Optional[str] = None):
        self.root_path = Path(root_path or os.environ["FILESYSTEM_ROOT_PATH"]).resolve()
        if not self.root_path.is_dir():
            raise ValueError(
                f"Filesystem root path '{self.root_path}' does not exist or is not a directory."
            )

    def list_media_objects(
        self,
        prefix: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        regex: Optional[str] = None,
    ) -> List[StoredMediaObject]:
        """
        List all files under the root path, optionally filtered by prefix and regex.
        Returns a list of StoredMediaObject instances with filesystem metadata.
        """
        # Walk the filesystem and collect file paths
        results = []
        regex_pattern = re.compile(regex) if regex else None

        for dirpath, _, filenames in os.walk(self.root_path):
            for filename in filenames:
                full_path = Path(dirpath) / filename
                rel_path = "/" + str(full_path.relative_to(self.root_path))

                # Apply prefix filter
                if prefix is not None and not rel_path.startswith(prefix):
                    continue

                # Apply regex filter if provided
                if regex_pattern and not regex_pattern.search(rel_path):
                    continue

                # Get file metadata
                stat = full_path.stat()
                last_modified = datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat()

                mime_type, _ = mimetypes.guess_type(rel_path)
                results.append(
                    StoredMediaObject(
                        object_key=rel_path,
                        last_modified=last_modified,
                        metadata={
                            "size": stat.st_size,
                            "created": datetime.fromtimestamp(
                                stat.st_ctime, tz=timezone.utc
                            ).isoformat(),
                            "mimetype": mime_type,
                        },
                    )
                )

        # Apply pagination
        return results[offset : offset + limit]

    def all_media_objects(
        self,
        prefix: Optional[str] = None,
        regex: Optional[str] = None,
    ) -> Iterable[StoredMediaObject]:
        """
        Yield all files under the root path, optionally filtered by prefix and regex.
        Returns an iterable of StoredMediaObject instances with filesystem metadata.
        """
        regex_pattern = re.compile(regex) if regex else None

        for dirpath, _, filenames in os.walk(self.root_path):
            for filename in filenames:
                full_path = Path(dirpath) / filename
                # Skip directories, symlinks, etc. - ensure it's a file
                if not full_path.is_file():
                    continue

                rel_path = "/" + str(full_path.relative_to(self.root_path))

                # Apply prefix filter
                if prefix is not None and not rel_path.startswith(prefix):
                    continue

                # Apply regex filter if provided
                if regex_pattern and not regex_pattern.search(rel_path):
                    continue

                # Get file metadata
                stat = full_path.stat()
                last_modified = datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat()

                mime_type, _ = mimetypes.guess_type(rel_path)
                yield StoredMediaObject(
                    object_key=rel_path,
                    last_modified=last_modified,
                    metadata={
                        "size": stat.st_size,
                        "created": datetime.fromtimestamp(
                            stat.st_ctime, tz=timezone.utc
                        ).isoformat(),
                        "mimetype": mime_type,
                    },
                )

    async def retrieve(self, object_key: str) -> bytes:
        """
        Retrieve the raw bytes of a file given its object key (relative path from root).
        """
        # Remove leading slash for filesystem path resolution
        rel_path = object_key.lstrip("/")
        file_path = self.root_path / rel_path
        if not file_path.is_file():
            raise FileNotFoundError(
                f"Object '{object_key}' not found in filesystem storage."
            )
        return file_path.read_bytes()

    def iter_object_bytes(self, object_key: str) -> Iterable[bytes]:
        """Yield bytes of a single media object in chunks.

        Args:
            object_key: Key of the object to retrieve

        Yields:
            Chunks of bytes from the object

        Raises:
            FileNotFoundError: If the object doesn't exist
        """
        file_path = self.root_path / object_key.lstrip("/")
        if not file_path.is_file():
            raise FileNotFoundError(
                f"Object '{object_key}' not found in filesystem storage."
            )

        with file_path.open("rb") as f:
            while chunk := f.read(4096):  # 4KB chunks
                yield chunk

    def count(
        self,
        prefix: Optional[str] = None,
        regex: Optional[str] = None,
    ) -> int:
        """
        Return the total count of media objects, optionally filtered by prefix and regex.
        """
        regex_pattern = re.compile(regex) if regex else None
        count = 0
        for dirpath, _, filenames in os.walk(self.root_path):
            for filename in filenames:
                full_path = Path(dirpath) / filename
                if not full_path.is_file():
                    continue
                rel_path = "/" + str(full_path.relative_to(self.root_path))
                if prefix is not None and not rel_path.startswith(prefix):
                    continue
                if regex_pattern and not regex_pattern.search(rel_path):
                    continue
                count += 1
        return count
