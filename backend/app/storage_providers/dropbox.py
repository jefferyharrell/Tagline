import mimetypes
import os
import re
from typing import Iterable, List, Optional, cast

import dropbox
from dropbox.exceptions import ApiError, RateLimitError
from dropbox.files import FileMetadata, FolderMetadata, ListFolderResult

from app.schemas import StoredMediaObject
from app.storage_exceptions import StorageProviderException
from app.storage_providers.base import DirectoryItem, StorageProviderBase


class DropboxStorageProvider(StorageProviderBase):
    """
    Storage provider that lists and retrieves files from a Dropbox folder.
    The root path is set by the DROPBOX_ROOT_PATH environment variable.
    Object keys are relative paths from the root, starting with a slash.
    """

    provider_name: str = "Dropbox"

    def __init__(
        self,
        root_path: str,
        app_key: str,
        app_secret: str,
        refresh_token: str,
    ):
        """Initialize Dropbox provider with necessary credentials and root path."""
        self.root_path = root_path
        self.dbx = dropbox.Dropbox(
            app_key=app_key,
            app_secret=app_secret,
            oauth2_refresh_token=refresh_token,
        )

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
        try:
            # Compose the path to list
            if prefix:
                # Remove leading slash from prefix to avoid double-slash
                prefix_path = prefix.lstrip("/")
                list_path = os.path.join(self.root_path, prefix_path)
            else:
                # No prefix, use root path
                list_path = self.root_path
            
            # Special case: Dropbox root directory must be empty string
            if list_path == "/":
                list_path = ""

            items: List[DirectoryItem] = []
            
            # List the directory (non-recursive to get immediate children only)
            res = cast(
                ListFolderResult,
                self.dbx.files_list_folder(list_path, recursive=False),
            )

            for entry in res.entries:
                if isinstance(entry, FolderMetadata):
                    # This is a folder
                    items.append(DirectoryItem(
                        name=entry.name,
                        is_folder=True,
                        object_key=None,  # Folders don't have object keys
                        size=None,
                        last_modified=None,
                        mimetype=None,
                    ))
                elif isinstance(entry, FileMetadata):
                    # This is a file - calculate object key as relative path from root
                    if self.root_path == "/":
                        # Root is Dropbox root, use full path without leading slash
                        rel_path = entry.path_display.lstrip("/")
                    else:
                        # Root is subfolder, calculate relative path
                        rel_path = os.path.relpath(entry.path_display, self.root_path)
                        rel_path = rel_path.lstrip("/")
                    
                    mime_type, _ = mimetypes.guess_type(rel_path)
                    last_modified = (
                        entry.server_modified.isoformat()
                        if entry.server_modified
                        else None
                    )
                    
                    items.append(DirectoryItem(
                        name=entry.name,
                        is_folder=False,
                        object_key=rel_path,
                        size=entry.size,
                        last_modified=last_modified,
                        mimetype=mime_type,
                    ))

            # Sort items: folders first, then files, both alphabetically
            items.sort(key=lambda x: (not x.is_folder, x.name.lower()))
            
            return items

        except RateLimitError as e:
            raise StorageProviderException("Dropbox rate limit exceeded") from e
        except ApiError as e:
            if e.error and e.error.is_path() and e.error.get_path().is_not_found():
                # Directory doesn't exist, return empty list
                return []
            raise StorageProviderException(f"Dropbox API error: {e}") from e
        except Exception as e:
            raise StorageProviderException(f"Dropbox error: {e}") from e

    def list_media_objects(
        self,
        prefix: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        regex: Optional[str] = None,
    ) -> List[StoredMediaObject]:
        """
        List all files under the root path, optionally filtered by prefix and regex.
        Returns a list of StoredMediaObject instances with Dropbox metadata.
        """
        try:
            # Compose the path to list
            list_path = self.root_path
            if prefix:
                # Remove leading slash to avoid double-slash in Dropbox path
                prefix_path = prefix.lstrip("/")
                list_path = os.path.join(self.root_path, prefix_path)

            # Compile regex pattern if provided
            regex_pattern = re.compile(regex) if regex else None

            # Dropbox API returns up to 2,000 entries per call; handle pagination
            results: List[StoredMediaObject] = []
            has_more = True
            cursor = None

            while has_more and len(results) < (offset + limit):
                if cursor:
                    res = cast(
                        ListFolderResult, self.dbx.files_list_folder_continue(cursor)
                    )
                else:
                    res = cast(
                        ListFolderResult,
                        self.dbx.files_list_folder(list_path, recursive=True),
                    )

                for entry in res.entries:
                    if isinstance(entry, FileMetadata):
                        # Calculate object key as relative path from root
                        if self.root_path == "/":
                            # Root is Dropbox root, use full path without leading slash
                            rel_path = entry.path_display.lstrip("/")
                        else:
                            # Root is subfolder, calculate relative path
                            rel_path = os.path.relpath(entry.path_display, self.root_path)
                            rel_path = rel_path.lstrip("/")

                        # Apply regex filter if provided
                        if regex_pattern and not regex_pattern.search(rel_path):
                            continue

                        mime_type, _ = mimetypes.guess_type(rel_path)
                        last_modified = (
                            entry.server_modified.isoformat()
                            if entry.server_modified
                            else None
                        )

                        # Create StoredMediaObject with Dropbox metadata
                        results.append(
                            StoredMediaObject(
                                object_key=rel_path,
                                last_modified=last_modified,
                                metadata={
                                    "size": entry.size,
                                    "content_hash": getattr(
                                        entry, "content_hash", None
                                    ),
                                    "rev": getattr(entry, "rev", None),
                                    "client_modified": (
                                        (
                                            cm.isoformat()
                                            if (
                                                cm := getattr(
                                                    entry, "client_modified", None
                                                )
                                            )
                                            is not None
                                            else None
                                        )
                                    ),
                                    "mimetype": mime_type,
                                },
                            )
                        )

                has_more = res.has_more
                cursor = res.cursor

            # Apply pagination
            return results[offset : offset + limit]

        except RateLimitError as e:
            raise StorageProviderException("Dropbox rate limit exceeded") from e
        except ApiError as e:
            raise StorageProviderException(f"Dropbox API error: {e}") from e
        except Exception as e:
            raise StorageProviderException(f"Dropbox error: {e}") from e

    def all_media_objects(
        self,
        prefix: Optional[str] = None,
        regex: Optional[str] = None,
    ) -> Iterable[StoredMediaObject]:
        """
        Yield all files under the root path, optionally filtered by prefix and regex.
        Returns an iterable of StoredMediaObject instances with Dropbox metadata.
        """
        try:
            # Compose the path to list
            if prefix:
                # Remove leading slash from prefix to avoid double-slash
                prefix_path = prefix.lstrip("/")
                list_path = os.path.join(self.root_path, prefix_path)
            else:
                list_path = self.root_path
            
            # Special case: Dropbox root directory must be empty string
            if list_path == "/":
                list_path = ""

            # Compile regex pattern if provided
            regex_pattern = re.compile(regex) if regex else None

            # Dropbox API returns up to 2,000 entries per call; handle pagination
            has_more = True
            cursor = None

            while has_more:
                if cursor:
                    res = cast(
                        ListFolderResult, self.dbx.files_list_folder_continue(cursor)
                    )
                else:
                    res = cast(
                        ListFolderResult,
                        self.dbx.files_list_folder(list_path, recursive=True),
                    )

                for entry in res.entries:
                    if isinstance(entry, FileMetadata):
                        # Calculate object key as relative path from root
                        if self.root_path == "/":
                            # Root is Dropbox root, use full path without leading slash
                            rel_path = entry.path_display.lstrip("/")
                        else:
                            # Root is subfolder, calculate relative path
                            rel_path = os.path.relpath(entry.path_display, self.root_path)
                            rel_path = rel_path.lstrip("/")

                        # Apply regex filter if provided
                        if regex_pattern and not regex_pattern.search(rel_path):
                            continue

                        mime_type, _ = mimetypes.guess_type(rel_path)
                        last_modified = (
                            entry.server_modified.isoformat()
                            if entry.server_modified
                            else None
                        )

                        # Yield StoredMediaObject with Dropbox metadata
                        yield StoredMediaObject(
                            object_key=rel_path,
                            last_modified=last_modified,
                            metadata={
                                "size": entry.size,
                                "content_hash": getattr(entry, "content_hash", None),
                                "rev": getattr(entry, "rev", None),
                                "client_modified": (
                                    (
                                        cm.isoformat()
                                        if (
                                            cm := getattr(
                                                entry, "client_modified", None
                                            )
                                        )
                                        is not None
                                        else None
                                    )
                                ),
                                "mimetype": mime_type,
                            },
                        )

                has_more = res.has_more
                cursor = res.cursor

        except RateLimitError as e:
            raise StorageProviderException("Dropbox rate limit exceeded") from e
        except ApiError as e:
            raise StorageProviderException(f"Dropbox API error: {e}") from e
        except Exception as e:
            raise StorageProviderException(f"Dropbox error: {e}") from e

    async def retrieve(self, object_key: str) -> bytes:
        """
        Retrieve the raw bytes of a file given its object key (relative path from root).
        """
        try:
            # Remove leading slash from object key and join with root
            rel_path = object_key.lstrip("/")
            dropbox_path = os.path.join(self.root_path, rel_path)
            
            # Special case: if we're at Dropbox root, don't use empty string for file paths
            if self.root_path == "/" and rel_path:
                dropbox_path = "/" + rel_path
            from typing import Any, Tuple

            md_response = cast(
                Tuple[FileMetadata, Any], self.dbx.files_download(dropbox_path)
            )
            response = md_response[1]
            return response.content
        except RateLimitError as e:
            raise StorageProviderException("Dropbox rate limit exceeded") from e
        except ApiError as e:
            if e.error and e.error.is_path() and e.error.get_path().is_not_found():
                raise FileNotFoundError(
                    f"Object '{object_key}' not found in Dropbox storage."
                )
            raise StorageProviderException(f"Dropbox API error: {e}") from e
        except Exception as e:
            raise StorageProviderException(f"Dropbox error: {e}") from e

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
        try:
            # Remove leading slash from object key and join with root
            rel_path = object_key.lstrip("/")
            dropbox_path = os.path.join(self.root_path, rel_path)
            
            # Special case: if we're at Dropbox root, don't use empty string for file paths
            if self.root_path == "/" and rel_path:
                dropbox_path = "/" + rel_path
            from typing import Any, Tuple

            md_response = cast(
                Tuple[FileMetadata, Any], self.dbx.files_download(dropbox_path)
            )
            response = md_response[1]

            # Yield response content in chunks
            chunk_size = 4096  # 4KB chunks
            content = response.content
            if content is None:
                raise StorageProviderException("Dropbox returned empty response")

            for i in range(0, len(content), chunk_size):
                yield content[i : i + chunk_size]

        except ApiError as e:
            if e.error and e.error.is_path() and e.error.get_path().is_not_found():
                raise FileNotFoundError(
                    f"Object '{object_key}' not found in Dropbox storage."
                ) from e
            raise StorageProviderException(f"Dropbox API error: {e}") from e
        except Exception as e:
            raise StorageProviderException(f"Dropbox error: {e}") from e

    def count(
        self,
        prefix: Optional[str] = None,
        regex: Optional[str] = None,
    ) -> int:
        """
        Return the total count of media objects, optionally filtered by prefix and regex.
        Note: This requires paginating through all Dropbox entries matching the prefix,
        which might be slow for very large directories.
        """
        try:
            # Compose the path to list
            if prefix:
                # Remove leading slash from prefix to avoid double-slash
                prefix_path = prefix.lstrip("/")
                list_path = os.path.join(self.root_path, prefix_path)
            else:
                list_path = self.root_path
            
            # Special case: Dropbox root directory must be empty string
            if list_path == "/":
                list_path = ""

            # Compile regex pattern if provided
            regex_pattern = re.compile(regex) if regex else None

            count = 0
            has_more = True
            cursor = None

            while has_more:
                if cursor:
                    res = cast(
                        ListFolderResult, self.dbx.files_list_folder_continue(cursor)
                    )
                else:
                    # Use path=list_path, recursive=True only makes sense if prefix is a directory
                    # If prefix points to a file, list_folder might error or return empty.
                    # We count only FileMetadata instances returned.
                    res = cast(
                        ListFolderResult,
                        self.dbx.files_list_folder(list_path, recursive=True),
                    )

                for entry in res.entries:
                    if isinstance(entry, FileMetadata):
                        # Calculate object key as relative path from root
                        if self.root_path == "/":
                            # Root is Dropbox root, use full path without leading slash
                            rel_path = entry.path_display.lstrip("/")
                        else:
                            # Root is subfolder, calculate relative path
                            try:
                                rel_path = os.path.relpath(entry.path_display, self.root_path)
                                rel_path = rel_path.lstrip("/")
                            except ValueError:
                                # Handle cases where entry is not under root_path
                                continue

                        # Apply prefix filter strictly (covers cases where list_path was broad)
                        # Convert to object key format with leading slash for comparison
                        obj_key = "/" + rel_path if rel_path else "/"
                        if prefix is not None and not obj_key.startswith(prefix):
                            continue

                        # Apply regex filter if provided
                        if regex_pattern and not regex_pattern.search(rel_path):
                            continue

                        count += 1

                has_more = res.has_more
                cursor = res.cursor

            return count

        except RateLimitError as e:
            raise StorageProviderException("Dropbox rate limit exceeded") from e
        except ApiError as e:
            # If the path doesn't exist, count is 0
            if e.error and e.error.is_path() and e.error.get_path().is_not_found():
                return 0
            raise StorageProviderException(f"Dropbox API error: {e}") from e
        except Exception as e:
            raise StorageProviderException(f"Dropbox error: {e}") from e
