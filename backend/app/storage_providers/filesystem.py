import mimetypes
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

from app.schemas import StoredMediaObject
from app.storage_providers.base import DirectoryItem, StorageProviderBase
from app.structlog_config import get_logger

logger = get_logger(__name__)


class FilesystemStorageProvider(StorageProviderBase):
    """
    Storage provider that lists and retrieves files from a local filesystem root.
    The root path is set by the FILESYSTEM_ROOT_PATH environment variable.
    Object keys are relative paths from the root, starting with a slash.
    """

    provider_name: str = "Filesystem"

    def __init__(self, root_path: Optional[str] = None, excluded_prefixes: Optional[List[str]] = None):
        root_path_str = root_path or os.environ["FILESYSTEM_ROOT_PATH"]
        self.excluded_prefixes = excluded_prefixes or []
        logger.info(
            "Initializing Filesystem storage provider",
            provider_type="filesystem",
            operation="init",
            root_path=root_path_str,
            excluded_prefixes_count=len(self.excluded_prefixes),
        )

        try:
            self.root_path = Path(root_path_str).resolve()
            if not self.root_path.is_dir():
                logger.error(
                    "Filesystem root path does not exist or is not a directory",
                    provider_type="filesystem",
                    operation="init",
                    root_path=str(self.root_path),
                    status="failed",
                )
                raise ValueError(
                    f"Filesystem root path '{self.root_path}' does not exist or is not a directory."
                )
            logger.info(
                "Filesystem storage provider initialized successfully",
                provider_type="filesystem",
                operation="init",
                resolved_path=str(self.root_path),
                status="success",
            )
        except Exception as e:
            logger.error(
                "Failed to initialize filesystem storage provider",
                provider_type="filesystem",
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
        normalized_path = "/" + path.lstrip("/") if path else "/"
        
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
                if self._should_include_path(folder_path):
                    should_include = True
                else:
                    # Even if folder is excluded, check if it might contain non-excluded content
                    # This is important for navigation - we show parent folders of included content
                    for prefix in self.excluded_prefixes:
                        # If this folder is a parent of an excluded prefix, we need to check further
                        if prefix.startswith(folder_path + "/"):
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
            "Starting filesystem directory listing",
            provider_type="filesystem",
            operation="list_directory",
            prefix=prefix,
        )

        # Determine the directory to list
        if prefix:
            # Remove leading slash for filesystem path resolution
            prefix_path = prefix.lstrip("/")
            target_dir = self.root_path / prefix_path
        else:
            target_dir = self.root_path

        logger.debug(
            "Resolved filesystem path for listing",
            provider_type="filesystem",
            operation="list_directory",
            target_dir=str(target_dir),
            prefix=prefix,
        )

        if not target_dir.is_dir():
            # Directory doesn't exist, return empty list
            logger.debug(
                "Directory does not exist, returning empty list",
                provider_type="filesystem",
                operation="list_directory",
                target_dir=str(target_dir),
            )
            return []

        items: List[DirectoryItem] = []

        try:
            # List immediate children only (no recursion)
            for item_path in target_dir.iterdir():
                if item_path.is_dir():
                    # This is a folder
                    items.append(
                        DirectoryItem(
                            name=item_path.name,
                            is_folder=True,
                            object_key=None,  # Folders don't have object keys
                            size=None,
                            last_modified=None,
                            mimetype=None,
                        )
                    )
                elif item_path.is_file():
                    # This is a file
                    rel_path = "/" + str(item_path.relative_to(self.root_path))
                    stat = item_path.stat()
                    last_modified = datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat()
                    mime_type, _ = mimetypes.guess_type(rel_path)

                    items.append(
                        DirectoryItem(
                            name=item_path.name,
                            is_folder=False,
                            object_key=rel_path,
                            size=stat.st_size,
                            last_modified=last_modified,
                            mimetype=mime_type,
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
                "Filesystem directory listing completed",
                provider_type="filesystem",
                operation="list_directory",
                duration_ms=duration * 1000,
                folders_count=folders_count,
                files_count=files_count,
                total_items=len(filtered_items),
                original_items=original_count,
                filtered_out=filtered_count,
                prefix=prefix,
                target_dir=str(target_dir),
            )

            return filtered_items

        except (PermissionError, OSError) as e:
            # Handle permission errors or other OS errors
            logger.warning(
                "Filesystem access error",
                provider_type="filesystem",
                operation="list_directory",
                error_type="access_error",
                target_dir=str(target_dir),
                error=str(e),
            )
            return []
        except Exception as e:
            logger.error(
                "Unexpected error during filesystem directory listing",
                provider_type="filesystem",
                operation="list_directory",
                error_type="unexpected",
                target_dir=str(target_dir),
                error=str(e),
                error_class=type(e).__name__,
            )
            return []

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
        start_time = time.time()
        logger.debug(
            "Starting filesystem media objects listing",
            provider_type="filesystem",
            operation="list_media_objects",
            prefix=prefix,
            limit=limit,
            offset=offset,
            regex=regex
        )

        try:
            # Walk the filesystem and collect file paths
            results = []
            regex_pattern = re.compile(regex) if regex else None
            if regex_pattern:
                logger.debug(
                    "Compiled regex pattern",
                    provider_type="filesystem",
                    operation="list_media_objects",
                    regex=regex
                )

            processed_files = 0

            for dirpath, _, filenames in os.walk(self.root_path):
                for filename in filenames:
                    processed_files += 1
                    full_path = Path(dirpath) / filename
                    rel_path = "/" + str(full_path.relative_to(self.root_path))

                    # Apply prefix filter
                    if prefix is not None and not rel_path.startswith(prefix):
                        continue

                    # Apply regex filter if provided
                    if regex_pattern and not regex_pattern.search(rel_path):
                        continue
                    
                    # Apply prefix exclusion filter
                    if not self._should_include_path(rel_path):
                        continue

                    # Get file metadata
                    try:
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
                    except (OSError, PermissionError) as e:
                        logger.warning(
                            "Failed to get file metadata",
                            provider_type="filesystem",
                            operation="list_media_objects",
                            error_type="metadata_error",
                            file_path=str(full_path),
                            error=str(e)
                        )
                        continue

            # Apply pagination
            paginated_results = results[offset : offset + limit]

            duration = time.time() - start_time
            logger.info(
                "Filesystem media objects listing completed",
                provider_type="filesystem",
                operation="list_media_objects",
                duration_ms=duration * 1000,
                total_results=len(results),
                returned_results=len(paginated_results),
                processed_files=processed_files,
                prefix=prefix
            )

            return paginated_results

        except Exception as e:
            logger.error(
                "Unexpected error during filesystem media objects listing",
                provider_type="filesystem",
                operation="list_media_objects",
                error_type="unexpected",
                error=str(e),
                error_class=type(e).__name__
            )
            return []

    def all_media_objects(
        self,
        prefix: Optional[str] = None,
        regex: Optional[str] = None,
    ) -> Iterable[StoredMediaObject]:
        """
        Yield all files under the root path, optionally filtered by prefix and regex.
        Returns an iterable of StoredMediaObject instances with filesystem metadata.
        """
        start_time = time.time()
        logger.debug(
            "Starting filesystem all media objects iteration",
            provider_type="filesystem",
            operation="all_media_objects",
            prefix=prefix,
            regex=regex
        )

        try:
            regex_pattern = re.compile(regex) if regex else None
            if regex_pattern:
                logger.debug(
                    "Compiled regex pattern",
                    provider_type="filesystem",
                    operation="all_media_objects",
                    regex=regex
                )

            processed_files = 0
            yielded_count = 0

            for dirpath, _, filenames in os.walk(self.root_path):
                for filename in filenames:
                    processed_files += 1
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
                    
                    # Apply prefix exclusion filter
                    if not self._should_include_path(rel_path):
                        continue

                    # Get file metadata
                    try:
                        stat = full_path.stat()
                        last_modified = datetime.fromtimestamp(
                            stat.st_mtime, tz=timezone.utc
                        ).isoformat()

                        mime_type, _ = mimetypes.guess_type(rel_path)
                        yielded_count += 1
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
                    except (OSError, PermissionError) as e:
                        logger.warning(
                            "Failed to get file metadata during iteration",
                            provider_type="filesystem",
                            operation="all_media_objects",
                            error_type="metadata_error",
                            file_path=str(full_path),
                            error=str(e)
                        )
                        continue

            duration = time.time() - start_time
            logger.info(
                "Filesystem all media objects iteration completed",
                provider_type="filesystem",
                operation="all_media_objects",
                duration_ms=duration * 1000,
                yielded_count=yielded_count,
                processed_files=processed_files,
                prefix=prefix
            )

        except Exception as e:
            logger.error(
                "Unexpected error during filesystem all media objects iteration",
                provider_type="filesystem",
                operation="all_media_objects",
                error_type="unexpected",
                error=str(e),
                error_class=type(e).__name__
            )
            return

    async def retrieve(self, object_key: str) -> bytes:
        """
        Retrieve the raw bytes of a file given its object key (relative path from root).
        """
        start_time = time.time()
        logger.debug(
            "Starting filesystem file retrieval",
            provider_type="filesystem",
            operation="retrieve",
            object_key=object_key,
        )
        
        # Check if the file is excluded
        if not self._should_include_path("/" + object_key.lstrip("/")):
            logger.info(
                "File retrieval blocked by prefix filter",
                provider_type="filesystem",
                operation="retrieve",
                object_key=object_key,
                reason="excluded_prefix"
            )
            raise FileNotFoundError(f"File not found: {object_key}")

        try:
            # Remove leading slash for filesystem path resolution
            rel_path = object_key.lstrip("/")
            file_path = self.root_path / rel_path

            logger.debug(
                "Resolved filesystem path for retrieval",
                provider_type="filesystem",
                operation="retrieve",
                object_key=object_key,
                file_path=str(file_path),
            )

            if not file_path.is_file():
                logger.warning(
                    "File not found during retrieval",
                    provider_type="filesystem",
                    operation="retrieve",
                    error_type="not_found",
                    object_key=object_key,
                    file_path=str(file_path),
                )
                raise FileNotFoundError(
                    f"Object '{object_key}' not found in filesystem storage."
                )

            file_size = file_path.stat().st_size
            data = file_path.read_bytes()

            duration = time.time() - start_time
            logger.info(
                "Filesystem file retrieval completed",
                provider_type="filesystem",
                operation="retrieve",
                duration_ms=duration * 1000,
                file_size=file_size,
                object_key=object_key,
                file_path=str(file_path),
            )

            return data

        except FileNotFoundError:
            raise  # Re-raise FileNotFoundError as-is
        except Exception as e:
            logger.error(
                "Unexpected error during filesystem file retrieval",
                provider_type="filesystem",
                operation="retrieve",
                error_type="unexpected",
                object_key=object_key,
                error=str(e),
                error_class=type(e).__name__,
            )
            raise

    def iter_object_bytes(self, object_key: str) -> Iterable[bytes]:
        """Yield bytes of a single media object in chunks.

        Args:
            object_key: Key of the object to retrieve

        Yields:
            Chunks of bytes from the object

        Raises:
            FileNotFoundError: If the object doesn't exist
        """
        start_time = time.time()
        logger.debug(
            "Starting filesystem streaming file retrieval",
            provider_type="filesystem",
            operation="iter_object_bytes",
            object_key=object_key
        )
        
        # Check if the file is excluded
        if not self._should_include_path("/" + object_key.lstrip("/")):
            logger.info(
                "Streaming retrieval blocked by prefix filter",
                provider_type="filesystem",
                operation="iter_object_bytes",
                object_key=object_key,
                reason="excluded_prefix"
            )
            raise FileNotFoundError(f"File not found: {object_key}")

        try:
            file_path = self.root_path / object_key.lstrip("/")

            logger.debug(
                "Resolved filesystem path for streaming",
                provider_type="filesystem",
                operation="iter_object_bytes",
                object_key=object_key,
                file_path=str(file_path)
            )

            if not file_path.is_file():
                logger.warning(
                    "File not found during streaming retrieval",
                    provider_type="filesystem",
                    operation="iter_object_bytes",
                    error_type="not_found",
                    object_key=object_key,
                    file_path=str(file_path)
                )
                raise FileNotFoundError(
                    f"Object '{object_key}' not found in filesystem storage."
                )

            file_size = file_path.stat().st_size
            chunks_yielded = 0

            with file_path.open("rb") as f:
                while chunk := f.read(4096):  # 4KB chunks
                    chunks_yielded += 1
                    yield chunk

            duration = time.time() - start_time
            logger.info(
                "Filesystem streaming retrieval completed",
                provider_type="filesystem",
                operation="iter_object_bytes",
                duration_ms=duration * 1000,
                file_size=file_size,
                chunks_yielded=chunks_yielded,
                object_key=object_key
            )

        except FileNotFoundError:
            raise  # Re-raise FileNotFoundError as-is
        except Exception as e:
            logger.error(
                "Unexpected error during filesystem streaming retrieval",
                provider_type="filesystem",
                operation="iter_object_bytes",
                error_type="unexpected",
                object_key=object_key,
                error=str(e),
                error_class=type(e).__name__
            )
            raise

    def count(
        self,
        prefix: Optional[str] = None,
        regex: Optional[str] = None,
    ) -> int:
        """
        Return the total count of media objects, optionally filtered by prefix and regex.
        """
        start_time = time.time()
        logger.debug(
            "Starting filesystem count operation",
            provider_type="filesystem",
            operation="count",
            prefix=prefix,
            regex=regex
        )

        try:
            regex_pattern = re.compile(regex) if regex else None
            if regex_pattern:
                logger.debug(
                    "Compiled regex pattern",
                    provider_type="filesystem",
                    operation="count",
                    regex=regex
                )

            count = 0
            processed_files = 0

            for dirpath, _, filenames in os.walk(self.root_path):
                for filename in filenames:
                    processed_files += 1
                    full_path = Path(dirpath) / filename
                    if not full_path.is_file():
                        continue
                    rel_path = "/" + str(full_path.relative_to(self.root_path))
                    if prefix is not None and not rel_path.startswith(prefix):
                        continue
                    if regex_pattern and not regex_pattern.search(rel_path):
                        continue
                    # Apply prefix exclusion filter
                    if not self._should_include_path(rel_path):
                        continue
                    count += 1

            duration = time.time() - start_time
            logger.info(
                "Filesystem count operation completed",
                provider_type="filesystem",
                operation="count",
                duration_ms=duration * 1000,
                objects_found=count,
                processed_files=processed_files,
                prefix=prefix
            )

            return count

        except Exception as e:
            logger.error(
                "Unexpected error during filesystem count operation",
                provider_type="filesystem",
                operation="count",
                error_type="unexpected",
                error=str(e),
                error_class=type(e).__name__
            )
            return 0
