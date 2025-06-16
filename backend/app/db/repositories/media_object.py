"""Repository for managing MediaObject persistence."""

import json
from datetime import datetime
from typing import List, Optional

from natsort import natsorted
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.domain_media_object import MediaObjectRecord
from app.models import IngestionStatus, ORMMediaObject
from app.structlog_config import get_logger

logger = get_logger(__name__)


class MediaObjectNotFound(Exception):
    """Raised when a MediaObject is not found for update/save."""

    pass


class MediaObjectRepository:
    """Handles database operations for MediaObject models."""

    def __init__(self, db: Session):
        """Initializes the repository with a database session."""
        self.db = db
        logger.debug(
            "Repository initialized",
            operation="db_repository_init",
            repository="media_object"
        )

    def get_by_object_key(self, object_key: str) -> Optional[MediaObjectRecord]:
        """Retrieves a MediaObjectRecord by its object_key (primary key)."""
        assert object_key is not None, "object_key must not be None"
        try:
            logger.debug(
                "Querying MediaObject by key",
                operation="db_query",
                table="media_objects",
                object_key=object_key
            )
            orm_obj = (
                self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            )
            if orm_obj:
                logger.debug(
                    "MediaObject found",
                    operation="db_query",
                    table="media_objects",
                    object_key=orm_obj.object_key,
                    status="found"
                )
                return MediaObjectRecord.from_orm(orm_obj)
            else:
                logger.debug(
                    "MediaObject not found",
                    operation="db_query",
                    table="media_objects",
                    object_key=object_key,
                    status="not_found"
                )
                return None
        except SQLAlchemyError as e:
            logger.error(
                "Database query failed",
                operation="db_query",
                table="media_objects",
                object_key=object_key,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return None

    def create_sparse(
        self,
        object_key: str,
        file_size: Optional[int] = None,
        file_mimetype: Optional[str] = None,
        file_last_modified: Optional[datetime] = None,
        provider_file_id: Optional[str] = None,
        provider_metadata: Optional[dict] = None,
    ) -> tuple[Optional[MediaObjectRecord], bool]:
        """Creates a sparse MediaObject record during discovery.

        Uses INSERT ... ON CONFLICT DO NOTHING to avoid duplicate key errors in logs.

        Args:
            object_key: The storage object key (without leading slash)
            file_size: File size in bytes
            file_mimetype: MIME type of the file
            file_last_modified: Last modified timestamp
            provider_file_id: Provider-specific unique file identifier
            provider_metadata: Provider-specific metadata

        Returns:
            Tuple of (MediaObjectRecord, was_created) where was_created is True if the object was newly created.
        """
        from datetime import datetime as dt

        from sqlalchemy import text

        from app.models import IngestionStatus

        try:
            logger.debug(
                "Creating sparse MediaObject",
                operation="db_create_sparse",
                table="media_objects",
                object_key=object_key,
                path_depth=object_key.count("/") + 1
            )

            # Calculate path depth (number of '/' separators + 1)
            path_depth = object_key.count("/") + 1

            # Use raw SQL with ON CONFLICT DO NOTHING to avoid duplicate key errors
            result = self.db.execute(
                text(
                    """
                    INSERT INTO media_objects 
                    (object_key, ingestion_status, object_metadata, file_size, 
                     file_mimetype, file_last_modified, path_depth, created_at, updated_at,
                     provider_file_id, provider_metadata)
                    VALUES 
                    (:object_key, :ingestion_status, CAST(:metadata AS jsonb), :file_size,
                     :file_mimetype, :file_last_modified, :path_depth, :created_at, :updated_at,
                     :provider_file_id, CAST(:provider_metadata AS jsonb))
                    ON CONFLICT (object_key) DO NOTHING
                    RETURNING object_key
                """
                ),
                {
                    "object_key": object_key,
                    "ingestion_status": IngestionStatus.PENDING.value,
                    "metadata": "{}",
                    "file_size": file_size,
                    "file_mimetype": file_mimetype,
                    "file_last_modified": file_last_modified,
                    "path_depth": path_depth,
                    "created_at": dt.utcnow(),
                    "updated_at": dt.utcnow(),
                    "provider_file_id": provider_file_id,
                    "provider_metadata": json.dumps(provider_metadata) if provider_metadata else "{}"
                },
            )

            self.db.commit()

            # Check if we actually inserted a row
            was_created = result.rowcount > 0
            if was_created:
                logger.info(
                    "Sparse MediaObject created",
                    operation="db_create_sparse",
                    table="media_objects",
                    object_key=object_key,
                    status="created"
                )
            else:
                logger.debug(
                    "MediaObject already exists",
                    operation="db_create_sparse",
                    table="media_objects",
                    object_key=object_key,
                    status="exists"
                )

            # Return the object (either newly created or existing) and creation status
            media_obj = self.get_by_object_key(object_key)
            return media_obj, was_created

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                "Sparse MediaObject creation failed",
                operation="db_create_sparse",
                table="media_objects",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return None, False

    def create(self, record: MediaObjectRecord) -> Optional[MediaObjectRecord]:
        """Creates a new MediaObjectRecord in the database or retrieves existing."""
        assert record.object_key is not None, "object_key must not be None"
        logger.debug(
            "Creating MediaObject record",
            operation="db_create",
            table="media_objects",
            object_key=record.object_key
        )
        orm_obj = record.to_orm()
        try:
            with self.db.begin_nested():
                self.db.add(orm_obj)
            self.db.commit()
            logger.info(
                "MediaObject created successfully",
                operation="db_create",
                table="media_objects",
                object_key=orm_obj.object_key,
                status="created"
            )
            return MediaObjectRecord.from_orm(orm_obj)
        except IntegrityError:
            self.db.rollback()
            logger.warning(
                "Integrity error on create, fetching existing",
                operation="db_create",
                table="media_objects",
                object_key=record.object_key,
                error_type="IntegrityError",
                status="exists"
            )
            existing_obj = self.get_by_object_key(record.object_key)
            if existing_obj:
                logger.info(
                    "Found existing MediaObject",
                    operation="db_create",
                    table="media_objects",
                    object_key=existing_obj.object_key,
                    status="found"
                )
            else:
                logger.error(
                    "IntegrityError but failed to fetch existing object",
                    operation="db_create",
                    table="media_objects",
                    object_key=record.object_key,
                    error_type="IntegrityError",
                    status="fetch_failed"
                )
            return existing_obj
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                "MediaObject creation failed",
                operation="db_create",
                table="media_objects",
                object_key=record.object_key,
                error_type=type(e).__name__,
                error_message=str(e)
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
                "Registering thumbnail",
                operation="db_update",
                table="media_objects",
                object_key=object_key,
                field="thumbnail_object_key"
            )

            # Update the media_object directly
            orm_obj = (
                self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            )
            if orm_obj is None:
                logger.error(
                    "MediaObject not found for thumbnail registration",
                    operation="db_update",
                    table="media_objects",
                    object_key=object_key,
                    field="thumbnail_object_key",
                    status="not_found"
                )
                return False

            orm_obj.thumbnail_object_key = s3_key  # type: ignore[assignment]
            orm_obj.updated_at = datetime.utcnow()  # type: ignore[assignment]

            self.db.commit()
            logger.info(
                "Thumbnail registered successfully",
                operation="db_update",
                table="media_objects",
                object_key=object_key,
                field="thumbnail_object_key",
                status="updated"
            )
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                "Thumbnail registration failed",
                operation="db_update",
                table="media_objects",
                object_key=object_key,
                field="thumbnail_object_key",
                error_type=type(e).__name__,
                error_message=str(e)
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
                "Registering proxy",
                operation="db_update",
                table="media_objects",
                object_key=object_key,
                field="proxy_object_key"
            )

            # Update the media_object directly
            orm_obj = (
                self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            )
            if orm_obj is None:
                logger.error(
                    "MediaObject not found for proxy registration",
                    operation="db_update",
                    table="media_objects",
                    object_key=object_key,
                    field="proxy_object_key",
                    status="not_found"
                )
                return False

            orm_obj.proxy_object_key = s3_key  # type: ignore[assignment]
            orm_obj.updated_at = datetime.utcnow()  # type: ignore[assignment]

            self.db.commit()
            logger.info(
                "Proxy registered successfully",
                operation="db_update",
                table="media_objects",
                object_key=object_key,
                field="proxy_object_key",
                status="updated"
            )
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                "Proxy registration failed",
                operation="db_update",
                table="media_objects",
                object_key=object_key,
                field="proxy_object_key",
                error_type=type(e).__name__,
                error_message=str(e)
            )
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

    def get_all(
        self, limit: int = 100, offset: int = 0, prefix: Optional[str] = None
    ) -> List[MediaObjectRecord]:
        """Retrieves a paginated list of all MediaObjectRecords with natural sort order."""
        try:
            logger.debug(
                "Querying all MediaObjects",
                operation="db_query",
                table="media_objects",
                limit=limit,
                offset=offset,
                prefix=prefix
            )
            query = self.db.query(ORMMediaObject)

            # Apply prefix filter if provided
            if prefix is not None:
                # Calculate expected path depth for this prefix
                # prefix="folder/" should have path_depth = number of "/" in prefix + 1
                expected_depth = prefix.count("/") + 1

                # Use optimized prefix matching with path depth filter
                query = query.filter(
                    ORMMediaObject.object_key.like(f"{prefix}%")
                ).filter(ORMMediaObject.path_depth == expected_depth)
            else:
                # For root level (prefix is None), only return files with path_depth = 1
                query = query.filter(ORMMediaObject.path_depth == 1)

            # Natural sort using the indexed expression - should be fast now
            orm_objs = (
                query.order_by(
                    func.regexp_replace(
                        ORMMediaObject.object_key, r"(\d+)", r"000000000\1", "g"
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
            logger.debug(
                "MediaObjects query completed",
                operation="db_query",
                table="media_objects",
                records_found=len(records)
            )
            return records
        except SQLAlchemyError as e:
            logger.error(
                "Query all MediaObjects failed",
                operation="db_query",
                table="media_objects",
                error_type=type(e).__name__,
                error_message=str(e)
            )
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
            orm_obj = (
                self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            )
            if orm_obj is None:
                logger.error(
                    "MediaObject not found for status update",
                    operation="db_update",
                    table="media_objects",
                    object_key=object_key,
                    field="ingestion_status",
                    status="not_found"
                )
                return False

            orm_obj.ingestion_status = status  # type: ignore[assignment]
            orm_obj.updated_at = datetime.utcnow()  # type: ignore[assignment]

            self.db.commit()
            logger.info(
                "Ingestion status updated",
                operation="db_update",
                table="media_objects",
                object_key=object_key,
                field="ingestion_status",
                new_status=status,
                status="updated"
            )
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                "Ingestion status update failed",
                operation="db_update",
                table="media_objects",
                field="ingestion_status", 
                error_type=type(e).__name__,
                error_message=str(e)
            )
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
            orm_obj = (
                self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            )
            if orm_obj is None:
                logger.error(
                    "MediaObject not found for metadata update",
                    operation="db_update",
                    table="media_objects",
                    object_key=object_key,
                    field="object_metadata",
                    status="not_found"
                )
                return False

            logger.info(
                "Before metadata update",
                operation="db_update",
                table="media_objects",
                object_key=object_key,
                field="object_metadata",
                phase="before"
            )
            logger.info(
                "Existing metadata before update",
                operation="db_update",
                table="media_objects",
                object_key=object_key,
                field="object_metadata",
                existing_metadata=orm_obj.object_metadata
            )
            logger.info(
                "New metadata to set",
                operation="db_update",
                table="media_objects",
                object_key=object_key,
                field="object_metadata",
                new_metadata=metadata
            )

            # Set the metadata directly (not merge, since PATCH endpoint already merged)
            orm_obj.object_metadata = metadata  # type: ignore[assignment]
            orm_obj.updated_at = datetime.utcnow()  # type: ignore[assignment]

            # Flush to see the changes before commit
            self.db.flush()
            logger.info(
                "Metadata updated in ORM",
                operation="db_update",
                table="media_objects",
                object_key=object_key,
                field="object_metadata",
                updated_metadata=orm_obj.object_metadata
            )

            self.db.commit()
            logger.info(
                "Metadata update completed",
                operation="db_update",
                table="media_objects",
                object_key=object_key,
                field="object_metadata",
                status="completed"
            )
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                "Metadata update failed",
                operation="db_update",
                table="media_objects",
                field="object_metadata",
                error_type=type(e).__name__,
                error_message=str(e)
            )
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
            orm_obj = (
                self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            )
            if orm_obj is None:
                logger.error(
                    "MediaObject not found for post-ingest update",
                    operation="db_update",
                    table="media_objects",
                    object_key=object_key,
                    phase="post_ingest",
                    status="not_found"
                )
                return False

            # Merge metadata
            if orm_obj.object_metadata:
                orm_obj.object_metadata.update(metadata)  # type: ignore[union-attr]
            else:
                orm_obj.object_metadata = metadata  # type: ignore[assignment]

            orm_obj.ingestion_status = IngestionStatus.COMPLETED.value  # type: ignore[assignment]
            orm_obj.updated_at = datetime.utcnow()  # type: ignore[assignment]

            self.db.commit()
            logger.info(
                "Post-ingest update completed",
                operation="db_update",
                table="media_objects",
                object_key=object_key,
                phase="post_ingest",
                status="completed"
            )
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                "Post-ingest update failed",
                operation="db_update",
                table="media_objects",
                phase="post_ingest",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return False

    def count(self, prefix: Optional[str] = None) -> int:
        """Returns the total count of MediaObjectRecords in the database."""
        try:
            logger.debug(
                "Counting MediaObjects",
                operation="db_query",
                table="media_objects",
                query_type="count",
                prefix=prefix
            )
            from sqlalchemy import func

            if prefix is not None:
                # Calculate expected path depth and use optimized counting
                expected_depth = prefix.count("/") + 1
                query = (
                    self.db.query(func.count(ORMMediaObject.object_key))
                    .filter(ORMMediaObject.object_key.like(f"{prefix}%"))
                    .filter(ORMMediaObject.path_depth == expected_depth)
                )
            else:
                # For root level (prefix is None), only count files with path_depth = 1
                query = self.db.query(func.count(ORMMediaObject.object_key)).filter(
                    ORMMediaObject.path_depth == 1
                )

            total = query.scalar() or 0
            logger.debug(
                "Count query completed",
                operation="db_query",
                table="media_objects",
                query_type="count",
                total_count=total
            )
            return total
        except SQLAlchemyError as e:
            logger.error(
                "Count query failed",
                operation="db_query",
                table="media_objects",
                query_type="count",
                error_type=type(e).__name__,
                error_message=str(e)
            )
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
            current = (
                self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            )
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
                ).filter(~ORMMediaObject.object_key.like(f"{prefix}%/%"))

            # Get all items in natural sort order to find position
            all_items = base_query.order_by(
                func.regexp_replace(ORMMediaObject.object_key, r"(\d+)", r"000000000\1")
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
            next_obj = (
                all_items[current_idx + 1] if current_idx < len(all_items) - 1 else None
            )

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
                "Adjacent MediaObjects query failed",
                operation="db_query",
                table="media_objects",
                query_type="adjacent",
                object_key=object_key,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return (None, None)

    def get_thumbnail_s3_key(self, object_key: str) -> Optional[tuple[str, str]]:
        """Get thumbnail S3 key for a media object.

        Returns:
            Tuple of (s3_key, mimetype) if found, None otherwise.
        """
        try:
            orm_obj = (
                self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            )
            if orm_obj and orm_obj.thumbnail_object_key:
                # Return mimetype as 'image/jpeg' since we don't store it separately anymore
                return (orm_obj.thumbnail_object_key, "image/jpeg")
            return None
        except SQLAlchemyError as e:
            logger.error(
                "Thumbnail lookup failed",
                operation="db_query",
                table="media_objects",
                object_key=object_key,
                field="thumbnail_object_key",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return None

    def get_proxy_s3_key(self, object_key: str) -> Optional[tuple[str, str]]:
        """Get proxy S3 key for a media object.

        Returns:
            Tuple of (s3_key, mimetype) if found, None otherwise.
        """
        try:
            orm_obj = (
                self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            )
            if orm_obj and orm_obj.proxy_object_key:
                # Return mimetype as 'image/jpeg' since we don't store it separately anymore
                return (orm_obj.proxy_object_key, "image/jpeg")
            return None
        except SQLAlchemyError as e:
            logger.error(
                "Proxy lookup failed",
                operation="db_query",
                table="media_objects",
                object_key=object_key,
                field="proxy_object_key",
                error_type=type(e).__name__,
                error_message=str(e)
            )
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

            logger.debug(
                "Executing search query",
                operation="db_query",
                table="media_objects",
                query_type="search",
                search_query=query,
                tsquery=tsquery
            )

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

            logger.debug(
                "Search query completed",
                operation="db_query",
                table="media_objects",
                query_type="search",
                total_results=total_count,
                returned_results=len(records)
            )
            return records, total_count

        except SQLAlchemyError as e:
            logger.error(
                "Search query failed",
                operation="db_query",
                table="media_objects",
                query_type="search",
                error_type=type(e).__name__,
                error_message=str(e)
            )
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
            logger.debug(
                "Getting objects by prefix",
                operation="db_query",
                table="media_objects",
                query_type="prefix",
                prefix=prefix
            )

            # Query for objects that start with prefix but don't have additional slashes
            query = self.db.query(ORMMediaObject).filter(
                ORMMediaObject.object_key.startswith(prefix)
            )

            # Exclude items in subfolders by filtering out paths with additional slashes
            if prefix:
                # For a non-empty prefix, exclude paths that have slashes after the prefix
                query = query.filter(~ORMMediaObject.object_key.like(f"{prefix}%/%"))
            else:
                # For root level (empty prefix), exclude any paths with slashes
                query = query.filter(~ORMMediaObject.object_key.contains("/"))

            # Apply natural sort order
            orm_objs = query.order_by(
                func.regexp_replace(
                    ORMMediaObject.object_key, r"(\d+)", r"000000000\1"
                ).label("natural_sort")
            ).all()

            records = [
                MediaObjectRecord.from_orm(obj, load_binary_fields=True)
                for obj in orm_objs
            ]

            logger.debug(
                "Prefix query completed",
                operation="db_query",
                table="media_objects",
                query_type="prefix",
                prefix=prefix,
                objects_found=len(records)
            )
            return records

        except SQLAlchemyError as e:
            logger.error(
                "Prefix query failed",
                operation="db_query",
                table="media_objects",
                query_type="prefix",
                prefix=prefix,
                error_type=type(e).__name__,
                error_message=str(e)
            )
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
            logger.debug(
                "Getting subfolders by prefix",
                operation="db_query",
                table="media_objects",
                query_type="subfolders",
                prefix=prefix
            )

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
                if "/" in remainder:
                    # Get the immediate subfolder name (everything before the first slash)
                    subfolder = remainder.split("/", 1)[0]
                    if subfolder:  # Avoid empty strings
                        subfolders.add(subfolder)

            # Convert to naturally sorted list
            result = natsorted(list(subfolders))

            logger.debug(
                "Subfolders query completed",
                operation="db_query",
                table="media_objects",
                query_type="subfolders",
                prefix=prefix,
                subfolders_found=len(result)
            )
            return result

        except SQLAlchemyError as e:
            logger.error(
                "Subfolders query failed",
                operation="db_query",
                table="media_objects",
                query_type="subfolders",
                prefix=prefix,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return []

    def delete_by_object_key(self, object_key: str) -> bool:
        """Delete a MediaObject by its object_key, including S3 cleanup.

        Args:
            object_key: The object key of the MediaObject to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            logger.debug(
                "Deleting MediaObject",
                operation="db_delete",
                table="media_objects",
                object_key=object_key
            )

            # First, get the media object to check for S3 keys
            orm_obj = (
                self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            )

            if not orm_obj:
                logger.debug(
                    "No MediaObject found to delete",
                    operation="db_delete",
                    table="media_objects",
                    object_key=object_key,
                    status="not_found"
                )
                return False

            # Clean up S3 objects if they exist
            try:
                from app.dependencies import get_s3_binary_storage

                s3_storage = get_s3_binary_storage()

                # Delete thumbnail and proxy from S3
                s3_storage.delete_binaries(object_key)
                logger.info(
                    "S3 binaries cleaned up",
                    operation="s3_cleanup",
                    object_key=object_key,
                    status="completed"
                )

            except Exception as e:
                # Log S3 cleanup failure but don't fail the whole operation
                logger.warning(
                    "S3 cleanup failed",
                    operation="s3_cleanup",
                    object_key=object_key,
                    error_type=type(e).__name__,
                    error_message=str(e)
                )

            # Delete the database record
            deleted_count = (
                self.db.query(ORMMediaObject).filter_by(object_key=object_key).delete()
            )

            if deleted_count > 0:
                self.db.commit()
                logger.info(
                    "MediaObject and S3 binaries deleted",
                    operation="db_delete",
                    table="media_objects",
                    object_key=object_key,
                    status="completed"
                )
                return True
            else:
                logger.debug(
                    "No MediaObject found for deletion",
                    operation="db_delete",
                    table="media_objects",
                    object_key=object_key,
                    status="not_found"
                )
                return False

        except SQLAlchemyError as e:
            logger.error(
                "MediaObject deletion failed",
                operation="db_delete",
                table="media_objects",
                object_key=object_key,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            self.db.rollback()
            return False
    
    def find_by_content_hash(self, content_hash: str) -> List[MediaObjectRecord]:
        """Find media objects by content hash."""
        if not content_hash:
            return []
        
        try:
            logger.debug(
                "Querying MediaObjects by content hash",
                operation="db_query",
                table="media_objects",
                content_hash=content_hash
            )
            orm_objs = (
                self.db.query(ORMMediaObject)
                .filter(ORMMediaObject.content_hash == content_hash)
                .all()
            )
            
            result = [MediaObjectRecord.from_orm(obj) for obj in orm_objs]
            logger.debug(
                "Found MediaObjects by content hash",
                operation="db_query",
                table="media_objects",
                content_hash=content_hash,
                count=len(result)
            )
            return result
            
        except SQLAlchemyError as e:
            logger.error(
                "Database error finding MediaObjects by content hash",
                operation="db_query",
                table="media_objects",
                content_hash=content_hash,
                error=str(e)
            )
            raise
    
    def find_by_provider_file_id(self, provider_file_id: str) -> Optional[MediaObjectRecord]:
        """Find media object by provider file ID."""
        if not provider_file_id:
            return None
        
        try:
            logger.debug(
                "Querying MediaObject by provider file ID",
                operation="db_query", 
                table="media_objects",
                provider_file_id=provider_file_id
            )
            orm_obj = (
                self.db.query(ORMMediaObject)
                .filter(ORMMediaObject.provider_file_id == provider_file_id)
                .first()
            )
            
            if orm_obj:
                result = MediaObjectRecord.from_orm(orm_obj)
                logger.debug(
                    "Found MediaObject by provider file ID",
                    operation="db_query",
                    table="media_objects", 
                    provider_file_id=provider_file_id,
                    object_key=result.object_key
                )
                return result
            else:
                logger.debug(
                    "No MediaObject found for provider file ID",
                    operation="db_query",
                    table="media_objects",
                    provider_file_id=provider_file_id
                )
                return None
                
        except SQLAlchemyError as e:
            logger.error(
                "Database error finding MediaObject by provider file ID",
                operation="db_query",
                table="media_objects",
                provider_file_id=provider_file_id,
                error=str(e)
            )
            raise
    
    def find_by_fingerprint(self, file_size: int, file_last_modified: Optional[datetime]) -> List[MediaObjectRecord]:
        """Find media objects by file size and modification time fingerprint."""
        try:
            logger.debug(
                "Querying MediaObjects by fingerprint",
                operation="db_query",
                table="media_objects",
                file_size=file_size,
                file_last_modified=file_last_modified.isoformat() if file_last_modified else None
            )
            
            query = self.db.query(ORMMediaObject).filter(ORMMediaObject.file_size == file_size)
            
            if file_last_modified:
                query = query.filter(ORMMediaObject.file_last_modified == file_last_modified)
            
            orm_objs = query.all()
            
            result = [MediaObjectRecord.from_orm(obj) for obj in orm_objs]
            logger.debug(
                "Found MediaObjects by fingerprint",
                operation="db_query",
                table="media_objects",
                file_size=file_size,
                count=len(result)
            )
            return result
            
        except SQLAlchemyError as e:
            logger.error(
                "Database error finding MediaObjects by fingerprint",
                operation="db_query",
                table="media_objects",
                file_size=file_size,
                error=str(e)
            )
            raise
    
    def handle_move(
        self, 
        old_object_key: str, 
        new_object_key: str,
        provider_file_id: Optional[str] = None,
        provider_metadata: Optional[dict] = None
    ) -> bool:
        """Handle moving a media object from old path to new path.
        
        Args:
            old_object_key: Current object_key of the media object
            new_object_key: New object_key to move to
            provider_file_id: Updated provider file ID if available
            provider_metadata: Updated provider metadata if available
            
        Returns:
            True if move was successful, False if object not found
        """
        try:
            logger.info(
                "Moving MediaObject",
                operation="db_update",
                table="media_objects",
                old_object_key=old_object_key,
                new_object_key=new_object_key
            )
            
            # Get the existing media object
            orm_obj = (
                self.db.query(ORMMediaObject)
                .filter(ORMMediaObject.object_key == old_object_key)
                .first()
            )
            
            if not orm_obj:
                logger.warning(
                    "MediaObject not found for move",
                    operation="db_update",
                    table="media_objects",
                    old_object_key=old_object_key,
                    status="not_found"
                )
                return False
            
            # Update previous_object_keys array
            previous_keys = orm_obj.previous_object_keys or []
            if old_object_key not in previous_keys:
                previous_keys.append(old_object_key)
            
            # Update the object
            orm_obj.object_key = new_object_key
            orm_obj.moved_from = old_object_key
            orm_obj.move_detected_at = datetime.utcnow()
            orm_obj.previous_object_keys = previous_keys
            orm_obj.path_depth = new_object_key.count('/') + 1 if new_object_key.startswith('/') else new_object_key.count('/') + 1
            
            if provider_file_id is not None:
                orm_obj.provider_file_id = provider_file_id
            if provider_metadata is not None:
                orm_obj.provider_metadata = provider_metadata
            
            self.db.commit()
            
            logger.info(
                "MediaObject moved successfully",
                operation="db_update",
                table="media_objects",
                old_object_key=old_object_key,
                new_object_key=new_object_key,
                status="completed"
            )
            return True
            
        except SQLAlchemyError as e:
            logger.error(
                "Failed to move MediaObject",
                operation="db_update",
                table="media_objects",
                old_object_key=old_object_key,
                new_object_key=new_object_key,
                error=str(e)
            )
            self.db.rollback()
            raise
    
    def update_content_hash(self, object_key: str, content_hash: str) -> bool:
        """Update the content hash for a media object.
        
        Args:
            object_key: The object key to update
            content_hash: SHA-256 hash of the content
            
        Returns:
            True if update was successful, False if object not found
        """
        try:
            logger.debug(
                "Updating content hash for MediaObject",
                operation="db_update",
                table="media_objects",
                object_key=object_key,
                content_hash=content_hash
            )
            
            result = (
                self.db.query(ORMMediaObject)
                .filter(ORMMediaObject.object_key == object_key)
                .update({"content_hash": content_hash})
            )
            
            if result > 0:
                self.db.commit()
                logger.debug(
                    "Content hash updated successfully",
                    operation="db_update", 
                    table="media_objects",
                    object_key=object_key,
                    content_hash=content_hash
                )
                return True
            else:
                logger.warning(
                    "MediaObject not found for content hash update",
                    operation="db_update",
                    table="media_objects", 
                    object_key=object_key
                )
                return False
                
        except SQLAlchemyError as e:
            logger.error(
                "Failed to update content hash",
                operation="db_update",
                table="media_objects",
                object_key=object_key,
                error=str(e)
            )
            self.db.rollback()
            raise
