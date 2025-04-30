import os
from typing import List, Optional

import dropbox
from dropbox.exceptions import ApiError, AuthError, RateLimitError
from dropbox.files import FileMetadata

from app.storage_exceptions import StorageProviderException
from app.storage_provider import StorageProviderBase


class DropboxStorageProvider(StorageProviderBase):
    """
    Storage provider that lists and retrieves files from a Dropbox folder.
    The root path is set by the DROPBOX_ROOT_PATH environment variable.
    Object keys are relative paths from the root, starting with a slash.
    """

    def __init__(self, root_path: Optional[str] = None):
        self.root_path = root_path or os.environ["DROPBOX_ROOT_PATH"]
        app_key = os.environ["DROPBOX_APP_KEY"]
        app_secret = os.environ["DROPBOX_APP_SECRET"]
        refresh_token = os.environ["DROPBOX_REFRESH_TOKEN"]
        try:
            self.dbx = dropbox.Dropbox(
                app_key=app_key,
                app_secret=app_secret,
                oauth2_refresh_token=refresh_token,
            )
        except AuthError as e:
            raise StorageProviderException(f"Dropbox authentication failed: {e}")

    async def list(
        self, prefix: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> list[str]:
        """
        List all files under the root path, optionally filtered by prefix.
        Returns a list of object keys (relative paths starting with '/').
        """
        try:
            # Compose the path to list
            list_path = self.root_path
            if prefix:
                # Remove leading slash to avoid double-slash in Dropbox path
                prefix_path = prefix.lstrip("/")
                list_path = os.path.join(self.root_path, prefix_path)
            # Dropbox API returns up to 2,000 entries per call; handle pagination
            results: List[str] = []
            has_more = True
            cursor = None
            from typing import cast

            from dropbox.files import ListFolderResult

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
                        results.append(rel_path)
                has_more = res.has_more
                cursor = res.cursor
            # Apply offset/limit after collecting
            return results[offset : offset + limit]
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
            from typing import Any, Tuple, cast

            from dropbox.files import FileMetadata

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
