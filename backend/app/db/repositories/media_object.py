"""Repository for managing MediaObject persistence."""

import logging
from typing import List, Optional
from datetime import datetime

from natsort import natsorted
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.domain_media_object import MediaObjectRecord
from app.models import ORMMediaObject, IngestionStatus

logger = logging.getLogger(__name__)


class MediaObjectNotFound(Exception):
    """Raised when a MediaObject is not found for update/save."""

    pass


class MediaObjectRepository:
    """Handles database operations for MediaObject models."""

    def __init__(self, db: Session):
        """Initializes the repository with a database session."""
        self.db = db
        logger.debug("MediaObjectRepository initialized successfully.")

    def get_by_object_key(self, object_key: str) -> Optional[MediaObjectRecord]:
        """Retrieves a MediaObjectRecord by its object_key (primary key)."""
        assert object_key is not None, "object_key must not be None"
        try:
            logger.debug(f"Querying for MediaObject with object_key: {object_key}")
            orm_obj = (
                self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            )
            if orm_obj:
                logger.debug(f"Found MediaObject: {orm_obj.object_key}")
                return MediaObjectRecord.from_orm(orm_obj)
            else:
                logger.debug("MediaObject not found for key: %s", object_key)
                return None
        except SQLAlchemyError as e:
            logger.error(f"Database error querying for object_key {object_key}: {e}")
            return None

    def create_sparse(self, object_key: str, file_size: Optional[int] = None,
                     file_mimetype: Optional[str] = None, 
                     file_last_modified: Optional[datetime] = None) -> tuple[Optional[MediaObjectRecord], bool]:
        """Creates a sparse MediaObject record during discovery.
        
        Uses INSERT ... ON CONFLICT DO NOTHING to avoid duplicate key errors in logs.
        
        Args:
            object_key: The storage object key (without leading slash)
            file_size: File size in bytes
            file_mimetype: MIME type of the file
            file_last_modified: Last modified timestamp
            
        Returns:
            Tuple of (MediaObjectRecord, was_created) where was_created is True if the object was newly created.
        """
        from app.models import IngestionStatus
        from datetime import datetime as dt
        from sqlalchemy import text
        
        try:
            logger.debug(f"Creating sparse MediaObject for key: {object_key}")
            
            # Calculate path depth (number of '/' separators + 1)
            path_depth = object_key.count('/') + 1
            
            # Use raw SQL with ON CONFLICT DO NOTHING to avoid duplicate key errors
            result = self.db.execute(
                text("""
                    INSERT INTO media_objects 
                    (object_key, ingestion_status, object_metadata, file_size, 
                     file_mimetype, file_last_modified, path_depth, created_at, updated_at)
                    VALUES 
                    (:object_key, :ingestion_status, CAST(:metadata AS jsonb), :file_size,
                     :file_mimetype, :file_last_modified, :path_depth, :created_at, :updated_at)
                    ON CONFLICT (object_key) DO NOTHING
                    RETURNING object_key
                """),
                {
                    "object_key": object_key,
                    "ingestion_status": IngestionStatus.PENDING.value,
                    "metadata": "{}",
                    "file_size": file_size,
                    "file_mimetype": file_mimetype,
                    "file_last_modified": file_last_modified,
                    "path_depth": path_depth,
                    "created_at": dt.utcnow(),
                    "updated_at": dt.utcnow()
                }
            )
            
            self.db.commit()
            
            # Check if we actually inserted a row
            was_created = result.rowcount > 0
            if was_created:
                logger.info(f"Successfully created sparse MediaObject for key: {object_key}")
            else:
                logger.debug(f"MediaObject already exists for key: {object_key}")
            
            # Return the object (either newly created or existing) and creation status
            media_obj = self.get_by_object_key(object_key)
            return media_obj, was_created
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating sparse MediaObject: {e}")
            return None, False

    def create(self, record: MediaObjectRecord) -> Optional[MediaObjectRecord]:
        """Creates a new MediaObjectRecord in the database or retrieves existing."""
        assert record.object_key is not None, "object_key must not be None"
        logger.debug(
            f"Attempting to create/get MediaObject for key: {record.object_key}"
        )
        orm_obj = record.to_orm()
        try:
            with self.db.begin_nested():
                self.db.add(orm_obj)
            self.db.commit()
            logger.info(
                f"Successfully created MediaObject for key: {orm_obj.object_key}"
            )
            return MediaObjectRecord.from_orm(orm_obj)
        except IntegrityError:
            self.db.rollback()
            logger.warning(
                f"IntegrityError on create for key {record.object_key}, likely exists. Fetching."
            )
            existing_obj = self.get_by_object_key(record.object_key)
            if existing_obj:
                logger.info(
                    f"Found existing MediaObject for key: {existing_obj.object_key}"
                )
            else:
                logger.error(
                    f"IntegrityError occurred but failed to fetch existing object for key {record.object_key}"
                )
            return existing_obj
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                f"Database error creating MediaObject for key {record.object_key}: {e}"
            )
            return None

    def register_thumbnail(
        self, object_key: str, s3_key: str, mimetype: str, size: Optional[int] = None
    ) -> bool:
        """Registers thumbnail S3 key for a MediaObject by updating the thumbnail_object_key column.

        Args:
            object_key: The object_key of the MediaObject.
            s3_key: The S3 key where the thumbnail is stored.
            mimetype: The mimetype of the thumbnail (ignored - kept for compatibility).
            size: Optional size of the thumbnail in bytes (ignored - kept for compatibility).

        Returns:
            True if the registration was successful, False otherwise.
        """
        try:
            logger.debug(
                f"Attempting to register thumbnail for object_key: {object_key}"
            )

            # Update the media_object directly
            orm_obj = self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            if orm_obj is None:
                logger.error(f"MediaObject with key {object_key} not found")
                return False
                
            orm_obj.thumbnail_object_key = s3_key  # type: ignore[assignment]
            orm_obj.updated_at = datetime.utcnow()  # type: ignore[assignment]

            self.db.commit()
            logger.info(
                f"Successfully registered thumbnail for object_key: {object_key}"
            )
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                f"Database error registering thumbnail for {object_key}: {e}"
            )
            return False

    def register_proxy(
        self, object_key: str, s3_key: str, mimetype: str, size: Optional[int] = None
    ) -> bool:
        """Registers proxy S3 key for a MediaObject by updating the proxy_object_key column.

        Args:
            object_key: The object_key of the MediaObject.
            s3_key: The S3 key where the proxy is stored.
            mimetype: The mimetype of the proxy (ignored - kept for compatibility).
            size: Optional size of the proxy in bytes (ignored - kept for compatibility).

        Returns:
            True if the registration was successful, False otherwise.
        """
        try:
            logger.debug(
                f"Attempting to register proxy for object_key: {object_key}"
            )

            # Update the media_object directly
            orm_obj = self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            if orm_obj is None:
                logger.error(f"MediaObject with key {object_key} not found")
                return False
                
            orm_obj.proxy_object_key = s3_key  # type: ignore[assignment]
            orm_obj.updated_at = datetime.utcnow()  # type: ignore[assignment]

            self.db.commit()
            logger.info(
                f"Successfully registered proxy for object_key: {object_key}"
            )
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error registering proxy for {object_key}: {e}")
            return False

    def get_or_create(self, record: MediaObjectRecord) -> Optional[MediaObjectRecord]:
        """Gets an existing MediaObjectRecord by object_key or creates it if not found.

        Relies on the atomic nature of the updated create() method.

        Args:
            record: The MediaObjectRecord domain object.

        Returns:
            The existing or newly created MediaObjectRecord, or None on error.
        """
        return self.create(record)

    def get_all(self, limit: int = 100, offset: int = 0, prefix: Optional[str] = None) -> List[MediaObjectRecord]:
        """Retrieves a paginated list of all MediaObjectRecords with natural sort order."""
        try:
            logger.debug(
                f"Querying for all MediaObjects with limit={limit}, offset={offset}, prefix={prefix}"
            )
            query = self.db.query(ORMMediaObject)
            
            # Apply prefix filter if provided
            if prefix is not None:
                # Calculate expected path depth for this prefix
                # prefix="folder/" should have path_depth = number of "/" in prefix + 1
                expected_depth = prefix.count('/') + 1
                
                # Use optimized prefix matching with path depth filter
                query = query.filter(
                    ORMMediaObject.object_key.like(f"{prefix}%")
                ).filter(
                    ORMMediaObject.path_depth == expected_depth
                )
            else:
                # For root level (prefix is None), only return files with path_depth = 1
                query = query.filter(
                    ORMMediaObject.path_depth == 1
                )
            
            # Natural sort using the indexed expression - should be fast now
            orm_objs = (
                query
                .order_by(
                    func.regexp_replace(
                        ORMMediaObject.object_key, 
                        r'(\d+)', 
                        r'000000000\1', 
                        'g'
                    )
                )
                .offset(offset)
                .limit(limit)
                .all()
            )
            
            # Convert to domain objects - thumbnail/proxy info comes from columns
            records = [
                MediaObjectRecord.from_orm(obj, load_binary_fields=False)
                for obj in orm_objs
            ]
            logger.debug(f"Found {len(records)} MediaObjects.")
            return records
        except SQLAlchemyError as e:
            logger.error(f"Database error querying for all MediaObjects: {e}")
            return []

    def update_ingestion_status(self, object_key: str, status: str) -> bool:
        """Updates the ingestion status of a MediaObject.
        
        Args:
            object_key: The object key of the MediaObject
            status: New ingestion status (pending, processing, completed, failed)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            orm_obj = self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            if orm_obj is None:
                logger.error(f"MediaObject with key {object_key} not found for status update")
                return False
                
            orm_obj.ingestion_status = status  # type: ignore[assignment]
            orm_obj.updated_at = datetime.utcnow()  # type: ignore[assignment]
            
            self.db.commit()
            logger.info(f"Updated ingestion status for {object_key} to {status}")
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating ingestion status: {e}")
            return False
            
    def update_metadata(self, object_key: str, metadata: dict) -> bool:
        """Updates metadata for a MediaObject without changing ingestion status.
        
        Args:
            object_key: The object key of the MediaObject
            metadata: The metadata to set (replaces existing metadata entirely)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            orm_obj = self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            if orm_obj is None:
                logger.error(f"MediaObject with key {object_key} not found for metadata update")
                return False
                
            logger.info(f"Before update - object_key: {object_key}")
            logger.info(f"Before update - existing metadata: {orm_obj.object_metadata}")
            logger.info(f"Before update - new metadata to set: {metadata}")
                
            # Set the metadata directly (not merge, since PATCH endpoint already merged)
            orm_obj.object_metadata = metadata  # type: ignore[assignment]
            orm_obj.updated_at = datetime.utcnow()  # type: ignore[assignment]
            
            # Flush to see the changes before commit
            self.db.flush()
            logger.info(f"After update - metadata in ORM: {orm_obj.object_metadata}")
            
            self.db.commit()
            logger.info(f"Successfully updated metadata for MediaObject {object_key}")
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating metadata: {e}")
            return False

    def update_after_ingestion(self, object_key: str, metadata: dict) -> bool:
        """Updates a MediaObject after successful ingestion.
        
        Args:
            object_key: The object key of the MediaObject
            metadata: The extracted metadata to merge
            
        Returns:
            True if successful, False otherwise
        """
        try:
            orm_obj = self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            if orm_obj is None:
                logger.error(f"MediaObject with key {object_key} not found for post-ingest update")
                return False
                
            # Merge metadata
            if orm_obj.object_metadata:
                orm_obj.object_metadata.update(metadata)  # type: ignore[union-attr]
            else:
                orm_obj.object_metadata = metadata  # type: ignore[assignment]
                
            orm_obj.ingestion_status = IngestionStatus.COMPLETED.value  # type: ignore[assignment]
            orm_obj.updated_at = datetime.utcnow()  # type: ignore[assignment]
            
            self.db.commit()
            logger.info(f"Updated MediaObject {object_key} after ingestion")
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating after ingestion: {e}")
            return False

    def count(self, prefix: Optional[str] = None) -> int:
        """Returns the total count of MediaObjectRecords in the database."""
        try:
            logger.debug(f"Querying for total count of MediaObjects with prefix={prefix}")
            from sqlalchemy import func
            
            if prefix is not None:
                # Calculate expected path depth and use optimized counting
                expected_depth = prefix.count('/') + 1
                query = self.db.query(func.count(ORMMediaObject.object_key)).filter(
                    ORMMediaObject.object_key.like(f"{prefix}%")
                ).filter(
                    ORMMediaObject.path_depth == expected_depth
                )
            else:
                # For root level (prefix is None), only count files with path_depth = 1
                query = self.db.query(func.count(ORMMediaObject.object_key)).filter(
                    ORMMediaObject.path_depth == 1
                )
            
            total = query.scalar() or 0
            logger.debug(f"Total count: {total}")
            return total
        except SQLAlchemyError as e:
            logger.error(f"Database error counting MediaObjects: {e}")
            return 0

    def get_adjacent(
        self, object_key: str
    ) -> tuple[Optional[MediaObjectRecord], Optional[MediaObjectRecord]]:
        """Gets the previous and next MediaObjectRecords relative to the given object_key.

        Returns a tuple of (previous, next) MediaObjectRecords based on natural sort order.
        Either or both may be None if at the beginning/end of the collection.
        """
        try:
            # Get the current media object to find its position
            current = self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            if not current:
                return (None, None)
                
            # Extract the folder path from the current object
            folder_path = "/".join(current.object_key.split("/")[:-1])
            prefix = f"{folder_path}/" if folder_path else ""

            # Build base query for same folder
            base_query = self.db.query(ORMMediaObject)
            if prefix:
                base_query = base_query.filter(
                    ORMMediaObject.object_key.startswith(prefix)
                ).filter(
                    ~ORMMediaObject.object_key.like(f"{prefix}%/%")
                )

            # Get all items in natural sort order to find position
            all_items = base_query.order_by(
                func.regexp_replace(
                    ORMMediaObject.object_key, 
                    r'(\d+)', 
                    r'000000000\1'
                )
            ).all()
            
            # Find current position
            current_idx = None
            for idx, item in enumerate(all_items):
                if item.object_key == object_key:
                    current_idx = idx
                    break
                    
            if current_idx is None:
                return (None, None)

            # Get previous and next based on position
            previous_obj = all_items[current_idx - 1] if current_idx > 0 else None
            next_obj = all_items[current_idx + 1] if current_idx < len(all_items) - 1 else None

            # Convert to domain objects
            previous = (
                MediaObjectRecord.from_orm(previous_obj, load_binary_fields=False)
                if previous_obj
                else None
            )
            next = (
                MediaObjectRecord.from_orm(next_obj, load_binary_fields=False)
                if next_obj
                else None
            )

            return (previous, next)
        except SQLAlchemyError as e:
            logger.error(
                f"Database error getting adjacent MediaObjects for key {object_key}: {e}"
            )
            return (None, None)

    def get_thumbnail_s3_key(self, object_key: str) -> Optional[tuple[str, str]]:
        """Get thumbnail S3 key for a media object.

        Returns:
            Tuple of (s3_key, mimetype) if found, None otherwise.
        """
        try:
            orm_obj = self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            if orm_obj and orm_obj.thumbnail_object_key:
                # Return mimetype as 'image/jpeg' since we don't store it separately anymore
                return (orm_obj.thumbnail_object_key, 'image/jpeg')
            return None
        except SQLAlchemyError as e:
            logger.error(f"Database error getting thumbnail for {object_key}: {e}")
            return None

    def get_proxy_s3_key(self, object_key: str) -> Optional[tuple[str, str]]:
        """Get proxy S3 key for a media object.

        Returns:
            Tuple of (s3_key, mimetype) if found, None otherwise.
        """
        try:
            orm_obj = self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            if orm_obj and orm_obj.proxy_object_key:
                # Return mimetype as 'image/jpeg' since we don't store it separately anymore
                return (orm_obj.proxy_object_key, 'image/jpeg')
            return None
        except SQLAlchemyError as e:
            logger.error(f"Database error getting proxy for {object_key}: {e}")
            return None

    def search(
        self, query: str, limit: int = 100, offset: int = 0
    ) -> tuple[List[MediaObjectRecord], int]:
        """Search media objects using full-text search.

        Args:
            query: Search query string (will be tokenized)
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            Tuple of (results, total_count)
        """
        try:
            if not query or not query.strip():
                # Empty query returns empty results
                return [], 0

            # Prepare the search query with prefix matching support
            # This ensures all terms must be present (AND logic) and supports partial word matching
            search_tokens = query.strip().split()
            # Add :* suffix for prefix matching on each token
            prefix_tokens = [f"{token}:*" for token in search_tokens]
            tsquery = " & ".join(prefix_tokens)

            logger.debug(f"Searching for: {query} (tsquery: {tsquery})")

            # First get the total count
            count_query = self.db.query(func.count(ORMMediaObject.object_key)).filter(
                text("search_vector @@ to_tsquery('english', :query)").bindparams(
                    query=tsquery
                )
            )
            total_count = count_query.scalar() or 0

            # Then get the paginated results with ranking
            results_query = (
                self.db.query(
                    ORMMediaObject,
                    func.ts_rank(
                        text("search_vector"), func.to_tsquery("english", tsquery)
                    ).label("rank"),
                )
                .filter(
                    text("search_vector @@ to_tsquery('english', :query)").bindparams(
                        query=tsquery
                    )
                )
                .order_by(text("rank DESC"), ORMMediaObject.created_at.desc())
                .offset(offset)
                .limit(limit)
            )

            # Execute query and convert to domain objects
            results = results_query.all()
            records = [
                MediaObjectRecord.from_orm(result[0], load_binary_fields=False)
                for result in results
            ]

            logger.debug(f"Found {total_count} total results, returning {len(records)}")
            return records, total_count

        except SQLAlchemyError as e:
            logger.error(f"Database error searching media objects: {e}")
            return [], 0

    def get_objects_with_prefix(self, prefix: str) -> List[MediaObjectRecord]:
        """Get all media objects that are direct children of the given prefix.
        
        This returns only files directly in the folder, not in subfolders.
        For example, prefix="folder/" returns ["folder/file1.jpg", "folder/file2.jpg"]
        but NOT ["folder/subfolder/file3.jpg"].
        
        Args:
            prefix: The folder prefix (should end with "/" for folders)
            
        Returns:
            List of MediaObjectRecord objects directly under the prefix
        """
        try:
            logger.debug(f"Getting objects with exact prefix: {prefix}")
            
            # Query for objects that start with prefix but don't have additional slashes
            query = self.db.query(ORMMediaObject).filter(
                ORMMediaObject.object_key.startswith(prefix)
            )
            
            # Exclude items in subfolders by filtering out paths with additional slashes
            if prefix:
                # For a non-empty prefix, exclude paths that have slashes after the prefix
                query = query.filter(
                    ~ORMMediaObject.object_key.like(f"{prefix}%/%")
                )
            else:
                # For root level (empty prefix), exclude any paths with slashes
                query = query.filter(
                    ~ORMMediaObject.object_key.contains("/")
                )
            
            # Apply natural sort order
            orm_objs = query.order_by(
                func.regexp_replace(
                    ORMMediaObject.object_key, 
                    r'(\d+)', 
                    r'000000000\1'
                ).label('natural_sort')
            ).all()
            
            records = [
                MediaObjectRecord.from_orm(obj, load_binary_fields=True)
                for obj in orm_objs
            ]
            
            logger.debug(f"Found {len(records)} objects with prefix: {prefix}")
            return records
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting objects with prefix {prefix}: {e}")
            return []

    def get_subfolders_with_prefix(self, prefix: str) -> List[str]:
        """Get immediate subfolders under the given prefix.
        
        This returns only the immediate subfolder names, not the full paths.
        For example, prefix="folder/" might return ["subfolder1", "subfolder2"].
        
        Args:
            prefix: The folder prefix to search under (empty string for root)
            
        Returns:
            List of immediate subfolder names (not full paths)
        """
        try:
            logger.debug(f"Getting subfolders with prefix: {prefix}")
            
            # Build query to find all objects under the prefix
            query = self.db.query(ORMMediaObject.object_key)
            
            if prefix:
                # For non-root folders, find objects that start with the prefix
                query = query.filter(ORMMediaObject.object_key.startswith(prefix))
            
            # Get all matching object keys
            all_keys = [row[0] for row in query.all()]
            
            # Extract unique immediate subfolders
            subfolders = set()
            prefix_len = len(prefix)
            
            for key in all_keys:
                # Get the part after the prefix
                remainder = key[prefix_len:]
                
                # If there's a slash in the remainder, it's in a subfolder
                if '/' in remainder:
                    # Get the immediate subfolder name (everything before the first slash)
                    subfolder = remainder.split('/', 1)[0]
                    if subfolder:  # Avoid empty strings
                        subfolders.add(subfolder)
            
            # Convert to naturally sorted list
            result = natsorted(list(subfolders))
            
            logger.debug(f"Found {len(result)} subfolders under prefix: {prefix}")
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting subfolders with prefix {prefix}: {e}")
            return []

    def delete_by_object_key(self, object_key: str) -> bool:
        """Delete a MediaObject by its object_key, including S3 cleanup.
        
        Args:
            object_key: The object key of the MediaObject to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            logger.debug(f"Deleting MediaObject with object_key: {object_key}")
            
            # First, get the media object to check for S3 keys
            orm_obj = self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            
            if not orm_obj:
                logger.debug(f"No MediaObject found to delete with object_key: {object_key}")
                return False
            
            # Clean up S3 objects if they exist
            try:
                from app.dependencies import get_s3_binary_storage
                s3_storage = get_s3_binary_storage()
                
                # Delete thumbnail and proxy from S3
                s3_storage.delete_binaries(object_key)
                logger.info(f"Cleaned up S3 binaries for: {object_key}")
                
            except Exception as e:
                # Log S3 cleanup failure but don't fail the whole operation
                logger.warning(f"Failed to cleanup S3 binaries for {object_key}: {e}")
            
            # Delete the database record
            deleted_count = (
                self.db.query(ORMMediaObject)
                .filter_by(object_key=object_key)
                .delete()
            )
            
            if deleted_count > 0:
                self.db.commit()
                logger.info(f"Successfully deleted MediaObject and S3 binaries: {object_key}")
                return True
            else:
                logger.debug(f"No MediaObject found to delete with object_key: {object_key}")
                return False
                
        except SQLAlchemyError as e:
            logger.error(f"Database error deleting MediaObject {object_key}: {e}")
            self.db.rollback()
            return False
