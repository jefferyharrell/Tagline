import mimetypes
import os
import re
from typing import Iterable, List, Optional, cast

import dropbox
from dropbox.exceptions import ApiError, RateLimitError
from dropbox.files import FileMetadata, ListFolderResult

from app.storage_exceptions import StorageProviderException
from app.storage_providers.base import StorageProviderBase
from app.storage_types import MediaObject


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

    def list_media_objects(
        self,
        prefix: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        regex: Optional[str] = None,
    ) -> List[MediaObject]:
        """
        List all files under the root path, optionally filtered by prefix and regex.
        Returns a list of MediaObject instances with Dropbox metadata.
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
            results: List[MediaObject] = []
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
                        rel_path = os.path.relpath(entry.path_display, self.root_path)
                        rel_path = "/" + rel_path.lstrip("/")

                        # Apply regex filter if provided
                        if regex_pattern and not regex_pattern.search(rel_path):
                            continue

                        mime_type, _ = mimetypes.guess_type(rel_path)
                        last_modified = (
                            entry.server_modified.isoformat()
                            if entry.server_modified
                            else None
                        )

                        # Create MediaObject with Dropbox metadata
                        results.append(
                            MediaObject(
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
    ) -> Iterable[MediaObject]:
        """
        Yield all files under the root path, optionally filtered by prefix and regex.
        Returns an iterable of MediaObject instances with Dropbox metadata.
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
                        rel_path = os.path.relpath(entry.path_display, self.root_path)
                        rel_path = "/" + rel_path.lstrip("/")

                        # Apply regex filter if provided
                        if regex_pattern and not regex_pattern.search(rel_path):
                            continue

                        mime_type, _ = mimetypes.guess_type(rel_path)
                        last_modified = (
                            entry.server_modified.isoformat()
                            if entry.server_modified
                            else None
                        )

                        # Yield MediaObject with Dropbox metadata
                        yield MediaObject(
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
            # Remove leading slash and join with root for Dropbox path
            rel_path = object_key.lstrip("/")
            dropbox_path = os.path.join(self.root_path, rel_path)
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
            list_path = self.root_path
            if prefix:
                # Ensure prefix starts with / and root_path doesn't end with /
                # Dropbox paths should not have double slashes
                norm_prefix = prefix.lstrip("/")
                norm_root = self.root_path.rstrip("/")
                list_path = (
                    f"{norm_root}/{norm_prefix}" if norm_root else f"/{norm_prefix}"
                )
                # If root_path is empty or '/', adjust list_path
                if not self.root_path or self.root_path == "/":
                    list_path = f"/{norm_prefix}"

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
                        # Normalize path_display for consistent comparison
                        entry_path = entry.path_display
                        if not entry_path.startswith("/"):
                            entry_path = "/" + entry_path

                        # Calculate relative path based on the original root_path
                        # Use os.path.relpath carefully with Dropbox paths
                        try:
                            rel_path = "/" + os.path.relpath(entry_path, self.root_path)
                        except (
                            ValueError
                        ):  # Handle cases where entry_path is not under root_path
                            continue

                        # Apply prefix filter strictly (covers cases where list_path was broad)
                        if prefix is not None and not rel_path.startswith(prefix):
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
