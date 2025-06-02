"""Repository for managing MediaObject persistence."""

import logging
from typing import List, Optional

from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.domain_media_object import MediaObjectRecord
from app.models import MediaBinaryType, ORMMediaBinary, ORMMediaObject

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

    def get_by_id(self, id) -> Optional[MediaObjectRecord]:
        """Retrieves a MediaObjectRecord by its UUID."""
        try:
            logger.debug(f"Querying for MediaObject with id: {id}")
            orm_obj = self.db.query(ORMMediaObject).filter_by(id=id).first()
            if orm_obj:
                logger.debug(f"Found MediaObject: {orm_obj.id}")
                return MediaObjectRecord.from_orm(orm_obj)
            else:
                logger.debug("MediaObject not found for id: %s", id)
                return None
        except SQLAlchemyError as e:
            logger.error(f"Database error querying for id {id}: {e}")
            return None

    def get_by_object_key(self, object_key: str) -> Optional[MediaObjectRecord]:
        """Retrieves a MediaObjectRecord by its object_key."""
        assert object_key is not None, "object_key must not be None"
        try:
            logger.debug(f"Querying for MediaObject with object_key: {object_key}")
            orm_obj = (
                self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            )
            if orm_obj:
                logger.debug(f"Found MediaObject: {orm_obj.id}")
                return MediaObjectRecord.from_orm(orm_obj)
            else:
                logger.debug("MediaObject not found for key: %s", object_key)
                return None
        except SQLAlchemyError as e:
            logger.error(f"Database error querying for object_key {object_key}: {e}")
            return None

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
                f"Successfully created MediaObject: {orm_obj.id} for key {orm_obj.object_key}"
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
                    f"Found existing MediaObject: {existing_obj.id} for key {existing_obj.object_key}"
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
        self, media_object_id, s3_key: str, mimetype: str, size: Optional[int] = None
    ) -> bool:
        """Registers thumbnail S3 key for a MediaObject by creating/updating a MediaBinary record.

        Args:
            media_object_id: The ID of the MediaObject.
            s3_key: The S3 key where the thumbnail is stored.
            mimetype: The mimetype of the thumbnail.
            size: Optional size of the thumbnail in bytes.

        Returns:
            True if the registration was successful, False otherwise.
        """
        try:
            logger.debug(
                f"Attempting to register thumbnail for media_object_id: {media_object_id}"
            )

            # Check if thumbnail record already exists
            existing_binary = (
                self.db.query(ORMMediaBinary)
                .filter_by(
                    media_object_id=media_object_id, type=MediaBinaryType.THUMBNAIL
                )
                .first()
            )

            if existing_binary:
                # Update existing
                existing_binary.s3_key = s3_key  # type: ignore[assignment]
                existing_binary.mimetype = mimetype  # type: ignore[assignment]
                existing_binary.size = size  # type: ignore[assignment]
            else:
                # Create new
                new_binary = ORMMediaBinary(
                    media_object_id=media_object_id,
                    type=MediaBinaryType.THUMBNAIL,
                    s3_key=s3_key,
                    mimetype=mimetype,
                    size=size,
                )
                self.db.add(new_binary)

            self.db.commit()
            logger.info(
                f"Successfully registered thumbnail for media_object_id: {media_object_id}"
            )
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                f"Database error registering thumbnail for {media_object_id}: {e}"
            )
            return False

    def register_proxy(
        self, media_object_id, s3_key: str, mimetype: str, size: Optional[int] = None
    ) -> bool:
        """Registers proxy S3 key for a MediaObject by creating/updating a MediaBinary record.

        Args:
            media_object_id: The ID of the MediaObject.
            s3_key: The S3 key where the proxy is stored.
            mimetype: The mimetype of the proxy.
            size: Optional size of the proxy in bytes.

        Returns:
            True if the registration was successful, False otherwise.
        """
        try:
            logger.debug(
                f"Attempting to register proxy for media_object_id: {media_object_id}"
            )

            # Check if proxy record already exists
            existing_binary = (
                self.db.query(ORMMediaBinary)
                .filter_by(media_object_id=media_object_id, type=MediaBinaryType.PROXY)
                .first()
            )

            if existing_binary:
                # Update existing
                existing_binary.s3_key = s3_key  # type: ignore[assignment]
                existing_binary.mimetype = mimetype  # type: ignore[assignment]
                existing_binary.size = size  # type: ignore[assignment]
            else:
                # Create new
                new_binary = ORMMediaBinary(
                    media_object_id=media_object_id,
                    type=MediaBinaryType.PROXY,
                    s3_key=s3_key,
                    mimetype=mimetype,
                    size=size,
                )
                self.db.add(new_binary)

            self.db.commit()
            logger.info(
                f"Successfully registered proxy for media_object_id: {media_object_id}"
            )
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error registering proxy for {media_object_id}: {e}")
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
        """Retrieves a paginated list of all MediaObjectRecords."""
        try:
            logger.debug(
                f"Querying for all MediaObjects with limit={limit}, offset={offset}, prefix={prefix}"
            )
            query = self.db.query(ORMMediaObject)
            
            # Apply prefix filter if provided
            if prefix:
                query = query.filter(ORMMediaObject.object_key.startswith(prefix))
            
            orm_objs = (
                query
                .order_by(ORMMediaObject.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            records = [
                MediaObjectRecord.from_orm(obj, load_binary_fields=False)
                for obj in orm_objs
            ]
            logger.debug(f"Found {len(records)} MediaObjects.")
            return records
        except SQLAlchemyError as e:
            logger.error(f"Database error querying for all MediaObjects: {e}")
            return []

    def save(self, record: MediaObjectRecord) -> MediaObjectRecord:
        """
        Updates an existing MediaObjectRecord in the database.
        Raises MediaObjectNotFound if not found.
        Returns the updated MediaObjectRecord.
        """
        assert record.id is not None, "id must not be None for update/save"
        try:
            orm_obj = self.db.query(ORMMediaObject).filter_by(id=record.id).first()
            if orm_obj is None:
                raise MediaObjectNotFound(f"MediaObject with id {record.id} not found.")
            # Update fields
            from typing import cast

            if record.object_key is not None:
                orm_obj.object_key = cast(str, record.object_key)  # type: ignore[assignment]
            if record.metadata is not None:
                orm_obj.object_metadata = cast(dict, record.metadata)  # type: ignore[assignment]
            # updated_at expects a datetime
            from datetime import datetime

            if record.last_modified:
                try:
                    # Try to parse ISO8601 string to datetime
                    new_updated_at = datetime.fromisoformat(record.last_modified)
                    orm_obj.updated_at = new_updated_at  # type: ignore[assignment]
                except Exception:
                    pass  # fallback: do not update if parsing fails
            self.db.commit()
            return MediaObjectRecord.from_orm(orm_obj)
        except SQLAlchemyError:
            self.db.rollback()
            raise

    def count(self, prefix: Optional[str] = None) -> int:
        """Returns the total count of MediaObjectRecords in the database."""
        try:
            logger.debug(f"Querying for total count of MediaObjects with prefix={prefix}")
            query = self.db.query(ORMMediaObject)
            
            # Apply prefix filter if provided
            if prefix:
                query = query.filter(ORMMediaObject.object_key.startswith(prefix))
            
            total = query.count()
            logger.debug(f"Total count: {total}")
            return total
        except SQLAlchemyError as e:
            logger.error(f"Database error counting MediaObjects: {e}")
            return 0

    def get_adjacent(
        self, id
    ) -> tuple[Optional[MediaObjectRecord], Optional[MediaObjectRecord]]:
        """Gets the previous and next MediaObjectRecords relative to the given id.

        Returns a tuple of (previous, next) MediaObjectRecords.
        Either or both may be None if at the beginning/end of the collection.
        """
        try:
            # Get the current media object to find its position
            current = self.db.query(ORMMediaObject).filter_by(id=id).first()
            if not current:
                return (None, None)

            # Get the previous media object (newer than current, since we're showing newest first)
            previous_obj = (
                self.db.query(ORMMediaObject)
                .filter(ORMMediaObject.created_at > current.created_at)
                .order_by(ORMMediaObject.created_at)
                .first()
            )

            # Get the next media object (older than current, since we're showing newest first)
            next_obj = (
                self.db.query(ORMMediaObject)
                .filter(ORMMediaObject.created_at < current.created_at)
                .order_by(ORMMediaObject.created_at.desc())
                .first()
            )

            # Convert to domain objects (skip binary fields for performance)
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
                f"Database error getting adjacent MediaObjects for id {id}: {e}"
            )
            return (None, None)

    def get_thumbnail_s3_key(self, media_object_id) -> Optional[tuple[str, str]]:
        """Get thumbnail S3 key for a media object.

        Returns:
            Tuple of (s3_key, mimetype) if found, None otherwise.
        """
        try:
            binary = (
                self.db.query(ORMMediaBinary)
                .filter_by(
                    media_object_id=media_object_id, type=MediaBinaryType.THUMBNAIL
                )
                .first()
            )
            if binary:
                return (binary.s3_key, binary.mimetype)  # type: ignore[return-value]
            return None
        except SQLAlchemyError as e:
            logger.error(f"Database error getting thumbnail for {media_object_id}: {e}")
            return None

    def get_proxy_s3_key(self, media_object_id) -> Optional[tuple[str, str]]:
        """Get proxy S3 key for a media object.

        Returns:
            Tuple of (s3_key, mimetype) if found, None otherwise.
        """
        try:
            binary = (
                self.db.query(ORMMediaBinary)
                .filter_by(media_object_id=media_object_id, type=MediaBinaryType.PROXY)
                .first()
            )
            if binary:
                return (binary.s3_key, binary.mimetype)  # type: ignore[return-value]
            return None
        except SQLAlchemyError as e:
            logger.error(f"Database error getting proxy for {media_object_id}: {e}")
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
            count_query = self.db.query(func.count(ORMMediaObject.id)).filter(
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
