import mimetypes
import os
import re
import time
from typing import Iterable, List, Optional, cast

import dropbox
from dropbox.exceptions import ApiError, RateLimitError
from dropbox.files import FileMetadata, FolderMetadata, ListFolderResult

from app.schemas import StoredMediaObject
from app.storage_exceptions import StorageProviderException
from app.storage_providers.base import DirectoryItem, StorageProviderBase
from app.structlog_config import get_logger
from app.utils.path_normalization import normalize_object_key

logger = get_logger(__name__)


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
        excluded_prefixes: Optional[List[str]] = None,
    ):
        """Initialize Dropbox provider with necessary credentials and root path."""
        self.root_path = root_path
        self.excluded_prefixes = excluded_prefixes or []
        logger.info(
            "Initializing Dropbox storage provider",
            provider_type="dropbox",
            operation="init",
            root_path=root_path,
            excluded_prefixes_count=len(self.excluded_prefixes),
        )

        try:
            self.dbx = dropbox.Dropbox(
                app_key=app_key,
                app_secret=app_secret,
                oauth2_refresh_token=refresh_token,
            )
            logger.info(
                "Dropbox client initialized successfully",
                provider_type="dropbox",
                operation="init",
                status="success",
            )
        except Exception as e:
            logger.error(
                "Failed to initialize Dropbox client",
                provider_type="dropbox",
                operation="init",
                status="failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def _should_include_path(self, path: str) -> bool:
        """Check if a path should be included based on excluded prefixes.
        
        Args:
            path: The path to check (should already be normalized with leading /)
            
        Returns:
            True if the path should be included, False if it should be filtered out
        """
        if not self.excluded_prefixes:
            return True
        
        # Ensure path starts with / for consistent comparison
        if not path:
            normalized_path = "/"
        elif path.startswith("/"):
            normalized_path = path
        else:
            normalized_path = "/" + path
        
        # Check if path starts with any excluded prefix (exact case match)
        for prefix in self.excluded_prefixes:
            if normalized_path.startswith(prefix):
                return False
                
        return True
    
    def _filter_items(self, items: List[DirectoryItem], current_prefix: Optional[str]) -> List[DirectoryItem]:
        """Filter items based on excluded prefixes.
        
        Args:
            items: List of items to filter
            current_prefix: The current directory prefix being listed
            
        Returns:
            Filtered list of items
        """
        if not self.excluded_prefixes:
            return items
            
        filtered_items = []
        for item in items:
            if item.is_folder:
                # For folders, construct the full path
                if current_prefix:
                    folder_path = f"/{current_prefix.strip('/')}/{item.name}"
                else:
                    folder_path = f"/{item.name}"
                folder_path = "/" + folder_path.strip("/")
                
                # Check if folder path should be included
                # Also check if any non-excluded path might exist under this folder
                should_include = False
                
                # First check if the folder itself is excluded
                # For folders, also check with trailing slash to match prefix patterns
                folder_with_slash = folder_path + "/"
                path_check = self._should_include_path(folder_path)
                slash_check = self._should_include_path(folder_with_slash)
                
                
                if path_check and slash_check:
                    should_include = True
                else:
                    # Even if folder is excluded, check if it might contain non-excluded content
                    # This is important for navigation - we show parent folders of included content
                    for prefix in self.excluded_prefixes:
                        # If this folder is a parent of an excluded prefix, we need to check further
                        # But don't include the folder if it exactly matches the prefix
                        folder_with_trailing_slash = folder_path + "/"
                        prefix_starts_check = prefix.startswith(folder_with_trailing_slash)
                        prefix_not_equal_check = prefix != folder_with_trailing_slash
                        
                        
                        if prefix_starts_check and prefix_not_equal_check:
                            # This folder contains excluded content, but might also contain non-excluded
                            # For now, include it to allow navigation
                            should_include = True
                            break
                
                if should_include:
                    filtered_items.append(item)
                    
            elif item.object_key:
                # For files, check the object key
                if self._should_include_path(item.object_key):
                    filtered_items.append(item)
        
        return filtered_items

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
        start_time = time.time()
        logger.debug(
            "Starting directory listing",
            provider_type="dropbox",
            operation="list_directory",
            prefix=prefix,
        )

        try:
            # Compose the path to list
            if prefix:
                # Use prefix as-is (no leading slash expected)
                prefix_path = prefix
                list_path = os.path.join(self.root_path, prefix_path)
            else:
                # No prefix, use root path
                list_path = self.root_path

            # Special case: Dropbox root directory must be empty string
            if list_path == "/":
                list_path = ""

            logger.debug(
                "Resolved Dropbox path for listing",
                provider_type="dropbox",
                operation="list_directory",
                list_path=list_path,
                prefix=prefix,
            )
            items: List[DirectoryItem] = []

            # List the directory (non-recursive to get immediate children only)
            api_start = time.time()
            res = cast(
                ListFolderResult,
                self.dbx.files_list_folder(list_path, recursive=False),
            )
            api_duration = time.time() - api_start
            logger.debug(
                "Dropbox API call completed",
                provider_type="dropbox",
                operation="list_directory",
                api_duration_ms=api_duration * 1000,
                list_path=list_path,
            )

            for entry in res.entries:
                if isinstance(entry, FolderMetadata):
                    # This is a folder
                    items.append(
                        DirectoryItem(
                            name=entry.name,
                            is_folder=True,
                            object_key=None,  # Folders don't have object keys
                            size=None,
                            last_modified=None,
                            mimetype=None,
                        )
                    )
                elif isinstance(entry, FileMetadata):
                    # This is a file - calculate object key as relative path from root
                    if self.root_path == "/":
                        # Root is Dropbox root, use full path without leading slash
                        rel_path = entry.path_display.lstrip("/")
                    else:
                        # Root is subfolder, calculate relative path
                        rel_path = os.path.relpath(entry.path_display, self.root_path)
                    
                    # Normalize object key to ensure no leading slash
                    normalized_object_key = normalize_object_key(rel_path)

                    mime_type, _ = mimetypes.guess_type(normalized_object_key)
                    last_modified = (
                        entry.server_modified.isoformat()
                        if entry.server_modified
                        else None
                    )

                    items.append(
                        DirectoryItem(
                            name=entry.name,
                            is_folder=False,
                            object_key=normalized_object_key,
                            size=entry.size,
                            last_modified=last_modified,
                            mimetype=mime_type,
                            file_id=getattr(entry, "id", None),  # Dropbox file ID
                        )
                    )

            # Sort items: folders first, then files, both alphabetically
            items.sort(key=lambda x: (not x.is_folder, x.name.lower()))
            
            # Apply prefix filtering
            filtered_items = self._filter_items(items, prefix)
            
            duration = time.time() - start_time
            folders_count = sum(1 for item in filtered_items if item.is_folder)
            files_count = len(filtered_items) - folders_count
            original_count = len(items)
            filtered_count = original_count - len(filtered_items)
            
            logger.info(
                "Directory listing completed",
                provider_type="dropbox",
                operation="list_directory",
                duration_ms=duration * 1000,
                api_duration_ms=api_duration * 1000,
                folders_count=folders_count,
                files_count=files_count,
                total_items=len(filtered_items),
                original_items=original_count,
                filtered_out=filtered_count,
                prefix=prefix,
                list_path=list_path,
            )

            return filtered_items

        except RateLimitError as e:
            logger.warning(
                "Dropbox rate limit exceeded",
                provider_type="dropbox",
                operation="list_directory",
                error_type="rate_limit",
                list_path=list_path,
                error=str(e),
            )
            raise StorageProviderException("Dropbox rate limit exceeded") from e
        except ApiError as e:
            if e.error and e.error.is_path() and e.error.get_path().is_not_found():
                # Directory doesn't exist, return empty list
                logger.debug(
                    "Directory not found, returning empty list",
                    provider_type="dropbox",
                    operation="list_directory",
                    error_type="not_found",
                    list_path=list_path,
                )
                return []
            logger.error(
                "Dropbox API error",
                provider_type="dropbox",
                operation="list_directory",
                error_type="api_error",
                list_path=list_path,
                error=str(e),
            )
            raise StorageProviderException(f"Dropbox API error: {e}") from e
        except Exception as e:
            logger.error(
                "Unexpected error during directory listing",
                provider_type="dropbox",
                operation="list_directory",
                error_type="unexpected",
                list_path=list_path,
                error=str(e),
                error_class=type(e).__name__,
            )
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
        start_time = time.time()
        logger.debug(
            "Starting media objects listing",
            provider_type="dropbox",
            operation="list_media_objects",
            prefix=prefix,
            limit=limit,
            offset=offset,
            regex=regex,
        )

        try:
            # Compose the path to list
            list_path = self.root_path
            if prefix:
                # Use prefix as-is (no leading slash expected)
                prefix_path = prefix
                list_path = os.path.join(self.root_path, prefix_path)

            logger.debug(
                "Resolved Dropbox path for media listing",
                provider_type="dropbox",
                operation="list_media_objects",
                list_path=list_path,
                prefix=prefix,
            )

            # Compile regex pattern if provided
            regex_pattern = re.compile(regex) if regex else None
            if regex_pattern:
                logger.debug(
                    "Compiled regex pattern",
                    provider_type="dropbox",
                    operation="list_media_objects",
                    regex=regex,
                )

            # Dropbox API returns up to 2,000 entries per call; handle pagination
            results: List[StoredMediaObject] = []
            has_more = True
            cursor = None
            api_calls = 0

            while has_more and len(results) < (offset + limit):
                api_start = time.time()
                api_calls += 1

                if cursor:
                    logger.debug(
                        "Making Dropbox API continuation call",
                        provider_type="dropbox",
                        operation="list_media_objects",
                        api_call_number=api_calls,
                    )
                    res = cast(
                        ListFolderResult, self.dbx.files_list_folder_continue(cursor)
                    )
                else:
                    logger.debug(
                        "Making initial Dropbox API call for recursive listing",
                        provider_type="dropbox",
                        operation="list_media_objects",
                    )
                    res = cast(
                        ListFolderResult,
                        self.dbx.files_list_folder(list_path, recursive=True),
                    )

                api_duration = time.time() - api_start
                logger.debug(
                    "API call completed",
                    provider_type="dropbox",
                    operation="list_media_objects",
                    api_call_number=api_calls,
                    api_duration_ms=api_duration * 1000,
                    entries_count=len(res.entries),
                )

                for entry in res.entries:
                    if isinstance(entry, FileMetadata):
                        # Calculate object key as relative path from root
                        if self.root_path == "/":
                            # Root is Dropbox root, use full path without leading slash
                            rel_path = entry.path_display.lstrip("/")
                        else:
                            # Root is subfolder, calculate relative path
                            rel_path = os.path.relpath(
                                entry.path_display, self.root_path
                            )

                        # Normalize object key to ensure no leading slash
                        normalized_object_key = normalize_object_key(rel_path)

                        # Apply regex filter if provided
                        if regex_pattern and not regex_pattern.search(normalized_object_key):
                            continue
                        
                        # Apply prefix exclusion filter
                        if not self._should_include_path("/" + normalized_object_key):
                            continue

                        mime_type, _ = mimetypes.guess_type(normalized_object_key)
                        last_modified = (
                            entry.server_modified.isoformat()
                            if entry.server_modified
                            else None
                        )

                        # Create StoredMediaObject with Dropbox metadata
                        results.append(
                            StoredMediaObject(
                                object_key=normalized_object_key,
                                last_modified=last_modified,
                                file_id=getattr(entry, "id", None),  # Dropbox file ID for move detection
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
            paginated_results = results[offset : offset + limit]

            duration = time.time() - start_time
            logger.info(
                "Media objects listing completed",
                provider_type="dropbox",
                operation="list_media_objects",
                duration_ms=duration * 1000,
                total_results=len(results),
                returned_results=len(paginated_results),
                api_calls=api_calls,
                prefix=prefix,
                list_path=list_path,
            )

            return paginated_results

        except RateLimitError as e:
            logger.warning(
                "Dropbox rate limit exceeded",
                provider_type="dropbox",
                operation="list_media_objects",
                error_type="rate_limit",
                list_path=list_path,
                error=str(e)
            )
            raise StorageProviderException("Dropbox rate limit exceeded") from e
        except ApiError as e:
            logger.error(
                "Dropbox API error during media objects listing",
                provider_type="dropbox",
                operation="list_media_objects",
                error_type="api_error",
                list_path=list_path,
                error=str(e)
            )
            raise StorageProviderException(f"Dropbox API error: {e}") from e
        except Exception as e:
            logger.error(
                "Unexpected error during media objects listing",
                provider_type="dropbox",
                operation="list_media_objects",
                error_type="unexpected",
                list_path=list_path,
                error=str(e),
                error_class=type(e).__name__
            )
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
        start_time = time.time()
        logger.debug(
            "Starting all media objects iteration",
            provider_type="dropbox",
            operation="all_media_objects",
            prefix=prefix,
            regex=regex
        )

        try:
            # Compose the path to list
            if prefix:
                # Use prefix as-is (no leading slash expected)
                prefix_path = prefix
                list_path = os.path.join(self.root_path, prefix_path)
            else:
                list_path = self.root_path

            # Special case: Dropbox root directory must be empty string
            if list_path == "/":
                list_path = ""

            logger.debug(
                "Resolved Dropbox path for all media iteration",
                provider_type="dropbox",
                operation="all_media_objects",
                list_path=list_path
            )

            # Compile regex pattern if provided
            regex_pattern = re.compile(regex) if regex else None
            if regex_pattern:
                logger.debug(
                    "Compiled regex pattern",
                    provider_type="dropbox",
                    operation="list_media_objects",
                    regex=regex,
                )

            # Dropbox API returns up to 2,000 entries per call; handle pagination
            has_more = True
            cursor = None
            api_calls = 0
            yielded_count = 0

            while has_more:
                api_start = time.time()
                api_calls += 1

                if cursor:
                    logger.debug(
                        "Making Dropbox API continuation call",
                        provider_type="dropbox",
                        operation="all_media_objects",
                        api_call_number=api_calls
                    )
                    res = cast(
                        ListFolderResult, self.dbx.files_list_folder_continue(cursor)
                    )
                else:
                    logger.debug(
                        "Making initial Dropbox API call for recursive listing",
                        provider_type="dropbox",
                        operation="all_media_objects"
                    )
                    res = cast(
                        ListFolderResult,
                        self.dbx.files_list_folder(list_path, recursive=True),
                    )

                api_duration = time.time() - api_start
                logger.debug(
                    "API call completed",
                    provider_type="dropbox",
                    operation="all_media_objects",
                    api_call_number=api_calls,
                    api_duration_ms=api_duration * 1000,
                    entries_count=len(res.entries)
                )

                for entry in res.entries:
                    if isinstance(entry, FileMetadata):
                        # Calculate object key as relative path from root
                        if self.root_path == "/":
                            # Root is Dropbox root, use full path without leading slash
                            rel_path = entry.path_display.lstrip("/")
                        else:
                            # Root is subfolder, calculate relative path
                            rel_path = os.path.relpath(
                                entry.path_display, self.root_path
                            )
                        
                        # Normalize object key to ensure no leading slash
                        normalized_object_key = normalize_object_key(rel_path)

                        # Apply regex filter if provided
                        if regex_pattern and not regex_pattern.search(normalized_object_key):
                            continue
                        
                        # Apply prefix exclusion filter
                        if not self._should_include_path("/" + normalized_object_key):
                            continue

                        mime_type, _ = mimetypes.guess_type(normalized_object_key)
                        last_modified = (
                            entry.server_modified.isoformat()
                            if entry.server_modified
                            else None
                        )

                        # Yield StoredMediaObject with Dropbox metadata
                        yielded_count += 1
                        yield StoredMediaObject(
                            object_key=normalized_object_key,
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

            duration = time.time() - start_time
            logger.info(
                "All media objects iteration completed",
                provider_type="dropbox",
                operation="all_media_objects",
                duration_ms=duration * 1000,
                yielded_count=yielded_count,
                api_calls=api_calls,
                prefix=prefix
            )

        except RateLimitError as e:
            logger.warning(
                "Dropbox rate limit exceeded",
                provider_type="dropbox",
                operation="all_media_objects",
                error_type="rate_limit",
                list_path=list_path,
                error=str(e)
            )
            raise StorageProviderException("Dropbox rate limit exceeded") from e
        except ApiError as e:
            logger.error(
                "Dropbox API error during all media objects iteration",
                provider_type="dropbox",
                operation="all_media_objects",
                error_type="api_error",
                list_path=list_path,
                error=str(e)
            )
            raise StorageProviderException(f"Dropbox API error: {e}") from e
        except Exception as e:
            logger.error(
                "Unexpected error during all media objects iteration",
                provider_type="dropbox",
                operation="all_media_objects",
                error_type="unexpected",
                list_path=list_path,
                error=str(e),
                error_class=type(e).__name__
            )
            raise StorageProviderException(f"Dropbox error: {e}") from e

    async def retrieve(self, object_key: str) -> bytes:
        """
        Retrieve the raw bytes of a file given its object key (relative path from root).
        """
        start_time = time.time()
        logger.debug(
            "Starting file retrieval",
            provider_type="dropbox",
            operation="retrieve",
            object_key=object_key,
        )
        
        # Check if the file is excluded
        if not self._should_include_path("/" + object_key):
            logger.info(
                "File retrieval blocked by prefix filter",
                provider_type="dropbox",
                operation="retrieve",
                object_key=object_key,
                reason="excluded_prefix"
            )
            raise FileNotFoundError(f"File not found: {object_key}")

        try:
            # Use object key as-is (no leading slash expected)
            rel_path = object_key
            dropbox_path = os.path.join(self.root_path, rel_path)

            # Special case: if we're at Dropbox root, don't use empty string for file paths
            if self.root_path == "/" and rel_path:
                dropbox_path = "/" + rel_path

            logger.debug(
                "Resolved Dropbox path for retrieval",
                provider_type="dropbox",
                operation="retrieve",
                object_key=object_key,
                dropbox_path=dropbox_path,
            )

            from typing import Any, Tuple

            api_start = time.time()
            md_response = cast(
                Tuple[FileMetadata, Any], self.dbx.files_download(dropbox_path)
            )
            api_duration = time.time() - api_start

            response = md_response[1]
            file_size = len(response.content) if response.content else 0

            duration = time.time() - start_time
            logger.info(
                "File retrieval completed",
                provider_type="dropbox",
                operation="retrieve",
                duration_ms=duration * 1000,
                api_duration_ms=api_duration * 1000,
                file_size=file_size,
                object_key=object_key,
                dropbox_path=dropbox_path,
            )

            return response.content
        except RateLimitError as e:
            logger.warning(
                "Dropbox rate limit exceeded during file retrieval",
                provider_type="dropbox",
                operation="retrieve",
                error_type="rate_limit",
                object_key=object_key,
                error=str(e),
            )
            raise StorageProviderException("Dropbox rate limit exceeded") from e
        except ApiError as e:
            if e.error and e.error.is_path() and e.error.get_path().is_not_found():
                logger.warning(
                    "File not found during retrieval",
                    provider_type="dropbox",
                    operation="retrieve",
                    error_type="not_found",
                    object_key=object_key,
                    dropbox_path=dropbox_path,
                )
                raise FileNotFoundError(
                    f"Object '{object_key}' not found in Dropbox storage."
                )
            logger.error(
                "Dropbox API error during file retrieval",
                provider_type="dropbox",
                operation="retrieve",
                error_type="api_error",
                object_key=object_key,
                error=str(e),
            )
            raise StorageProviderException(f"Dropbox API error: {e}") from e
        except Exception as e:
            logger.error(
                "Unexpected error during file retrieval",
                provider_type="dropbox",
                operation="retrieve",
                error_type="unexpected",
                object_key=object_key,
                error=str(e),
                error_class=type(e).__name__,
            )
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
        start_time = time.time()
        logger.debug(
            "Starting streaming file retrieval",
            provider_type="dropbox",
            operation="iter_object_bytes",
            object_key=object_key
        )
        
        # Check if the file is excluded
        if not self._should_include_path("/" + object_key):
            logger.info(
                "Streaming retrieval blocked by prefix filter",
                provider_type="dropbox",
                operation="iter_object_bytes",
                object_key=object_key,
                reason="excluded_prefix"
            )
            raise FileNotFoundError(f"File not found: {object_key}")

        try:
            # Use object key as-is (no leading slash expected)
            rel_path = object_key
            dropbox_path = os.path.join(self.root_path, rel_path)

            # Special case: if we're at Dropbox root, don't use empty string for file paths
            if self.root_path == "/" and rel_path:
                dropbox_path = "/" + rel_path

            logger.debug(
                "Resolved Dropbox path for streaming",
                provider_type="dropbox",
                operation="iter_object_bytes",
                object_key=object_key,
                dropbox_path=dropbox_path
            )

            from typing import Any, Tuple

            api_start = time.time()
            md_response = cast(
                Tuple[FileMetadata, Any], self.dbx.files_download(dropbox_path)
            )
            api_duration = time.time() - api_start

            response = md_response[1]

            # Yield response content in chunks
            chunk_size = 4096  # 4KB chunks
            content = response.content
            if content is None:
                logger.error(
                    "Dropbox returned empty response",
                    provider_type="dropbox",
                    operation="iter_object_bytes",
                    object_key=object_key,
                    error_type="empty_response"
                )
                raise StorageProviderException("Dropbox returned empty response")

            total_size = len(content)
            chunks_yielded = 0

            for i in range(0, len(content), chunk_size):
                chunks_yielded += 1
                yield content[i : i + chunk_size]

            duration = time.time() - start_time
            logger.info(
                "Streaming retrieval completed",
                provider_type="dropbox",
                operation="iter_object_bytes",
                duration_ms=duration * 1000,
                api_duration_ms=api_duration * 1000,
                total_size=total_size,
                chunks_yielded=chunks_yielded,
                object_key=object_key
            )

        except ApiError as e:
            if e.error and e.error.is_path() and e.error.get_path().is_not_found():
                logger.warning(
                    "File not found during streaming retrieval",
                    provider_type="dropbox",
                    operation="iter_object_bytes",
                    error_type="not_found",
                    object_key=object_key,
                    dropbox_path=dropbox_path
                )
                raise FileNotFoundError(
                    f"Object '{object_key}' not found in Dropbox storage."
                ) from e
            logger.error(
                "Dropbox API error during streaming retrieval",
                provider_type="dropbox",
                operation="iter_object_bytes",
                error_type="api_error",
                object_key=object_key,
                error=str(e)
            )
            raise StorageProviderException(f"Dropbox API error: {e}") from e
        except Exception as e:
            logger.error(
                "Unexpected error during streaming retrieval",
                provider_type="dropbox",
                operation="iter_object_bytes",
                error_type="unexpected",
                object_key=object_key,
                error=str(e),
                error_class=type(e).__name__
            )
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
        start_time = time.time()
        logger.debug(
            "Starting count operation",
            provider_type="dropbox",
            operation="count",
            prefix=prefix,
            regex=regex
        )

        try:
            # Compose the path to list
            if prefix:
                # Use prefix as-is (no leading slash expected)
                prefix_path = prefix
                list_path = os.path.join(self.root_path, prefix_path)
            else:
                list_path = self.root_path

            # Special case: Dropbox root directory must be empty string
            if list_path == "/":
                list_path = ""

            logger.debug(
                "Resolved Dropbox path for count",
                provider_type="dropbox",
                operation="count",
                list_path=list_path
            )

            # Compile regex pattern if provided
            regex_pattern = re.compile(regex) if regex else None
            if regex_pattern:
                logger.debug(
                    "Compiled regex pattern",
                    provider_type="dropbox",
                    operation="list_media_objects",
                    regex=regex,
                )

            count = 0
            has_more = True
            cursor = None
            api_calls = 0

            while has_more:
                api_start = time.time()
                api_calls += 1

                if cursor:
                    logger.debug(
                        "Making Dropbox API continuation call",
                        provider_type="dropbox",
                        operation="count",
                        api_call_number=api_calls
                    )
                    res = cast(
                        ListFolderResult, self.dbx.files_list_folder_continue(cursor)
                    )
                else:
                    logger.debug(
                        "Making initial Dropbox API call for count",
                        provider_type="dropbox",
                        operation="count"
                    )
                    # Use path=list_path, recursive=True only makes sense if prefix is a directory
                    # If prefix points to a file, list_folder might error or return empty.
                    # We count only FileMetadata instances returned.
                    res = cast(
                        ListFolderResult,
                        self.dbx.files_list_folder(list_path, recursive=True),
                    )

                api_duration = time.time() - api_start
                logger.debug(
                    "API call completed for count",
                    provider_type="dropbox",
                    operation="count",
                    api_call_number=api_calls,
                    api_duration_ms=api_duration * 1000,
                    entries_count=len(res.entries)
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
                                rel_path = os.path.relpath(
                                    entry.path_display, self.root_path
                                )
                            except ValueError:
                                # Handle cases where entry is not under root_path
                                continue

                        # Normalize object key to ensure no leading slash
                        normalized_object_key = normalize_object_key(rel_path)

                        # Apply prefix filter strictly (covers cases where list_path was broad)
                        # Object key is normalized (no leading slash)
                        if prefix is not None and not normalized_object_key.startswith(prefix):
                            continue

                        # Apply regex filter if provided
                        if regex_pattern and not regex_pattern.search(rel_path):
                            continue
                        
                        # Apply prefix exclusion filter
                        if not self._should_include_path("/" + rel_path):
                            continue

                        count += 1

                has_more = res.has_more
                cursor = res.cursor

            duration = time.time() - start_time
            logger.info(
                "Count operation completed",
                provider_type="dropbox",
                operation="count",
                duration_ms=duration * 1000,
                objects_found=count,
                api_calls=api_calls,
                prefix=prefix
            )

            return count

        except RateLimitError as e:
            logger.warning(
                "Dropbox rate limit exceeded during count",
                provider_type="dropbox",
                operation="count",
                error_type="rate_limit",
                list_path=list_path,
                error=str(e)
            )
            raise StorageProviderException("Dropbox rate limit exceeded") from e
        except ApiError as e:
            # If the path doesn't exist, count is 0
            if e.error and e.error.is_path() and e.error.get_path().is_not_found():
                logger.debug(
                    "Path not found during count, returning 0",
                    provider_type="dropbox",
                    operation="count",
                    error_type="not_found",
                    list_path=list_path,
                    count=0
                )
                return 0
            logger.error(
                "Dropbox API error during count",
                provider_type="dropbox",
                operation="count",
                error_type="api_error",
                list_path=list_path,
                error=str(e)
            )
            raise StorageProviderException(f"Dropbox API error: {e}") from e
        except Exception as e:
            logger.error(
                "Unexpected error during count",
                provider_type="dropbox",
                operation="count",
                error_type="unexpected",
                list_path=list_path,
                error=str(e),
                error_class=type(e).__name__
            )
            raise StorageProviderException(f"Dropbox error: {e}") from e
