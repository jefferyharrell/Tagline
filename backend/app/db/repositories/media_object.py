"""Repository for managing MediaObject persistence."""

import logging
from typing import List, Optional

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, defer

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

    def update_thumbnail(
        self, object_key: str, thumbnail_bytes: bytes, thumbnail_mimetype: str
    ) -> bool:
        """Updates the thumbnail for a MediaObject by creating/updating a MediaBinary record.

        Args:
            object_key: The unique key of the MediaObject to update.
            thumbnail_bytes: The binary data of the thumbnail.
            thumbnail_mimetype: The mimetype of the thumbnail.

        Returns:
            True if the update was successful, False otherwise.
        """
        try:
            logger.debug(f"Attempting to update thumbnail for object_key: {object_key}")
            media_object = (
                self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            )
            if not media_object:
                logger.warning(
                    f"MediaObject not found for thumbnail update: {object_key}"
                )
                return False

            # Check if thumbnail binary already exists
            existing_binary = (
                self.db.query(ORMMediaBinary)
                .filter_by(media_object_id=media_object.id, type=MediaBinaryType.THUMBNAIL)
                .first()
            )
            
            if existing_binary:
                # Update existing
                existing_binary.data = thumbnail_bytes  # type: ignore[assignment]
                existing_binary.mimetype = thumbnail_mimetype  # type: ignore[assignment]
            else:
                # Create new
                new_binary = ORMMediaBinary(
                    media_object_id=media_object.id,
                    type=MediaBinaryType.THUMBNAIL,
                    data=thumbnail_bytes,
                    mimetype=thumbnail_mimetype
                )
                self.db.add(new_binary)
            
            self.db.commit()
            logger.info(f"Successfully updated thumbnail for {object_key}")
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating thumbnail for {object_key}: {e}")
            return False

    def update_proxy(
        self, object_key: str, proxy_bytes: bytes, proxy_mimetype: str
    ) -> bool:
        """Updates the proxy for a MediaObject by creating/updating a MediaBinary record.

        Args:
            object_key: The unique key of the MediaObject to update.
            proxy_bytes: The binary data of the proxy.
            proxy_mimetype: The mimetype of the proxy.

        Returns:
            True if the update was successful, False otherwise.
        """
        try:
            logger.debug(f"Attempting to update proxy for object_key: {object_key}")
            media_object = (
                self.db.query(ORMMediaObject).filter_by(object_key=object_key).first()
            )
            if not media_object:
                logger.warning(f"MediaObject not found for proxy update: {object_key}")
                return False

            # Check if proxy binary already exists
            existing_binary = (
                self.db.query(ORMMediaBinary)
                .filter_by(media_object_id=media_object.id, type=MediaBinaryType.PROXY)
                .first()
            )
            
            if existing_binary:
                # Update existing
                existing_binary.data = proxy_bytes  # type: ignore[assignment]
                existing_binary.mimetype = proxy_mimetype  # type: ignore[assignment]
            else:
                # Create new
                new_binary = ORMMediaBinary(
                    media_object_id=media_object.id,
                    type=MediaBinaryType.PROXY,
                    data=proxy_bytes,
                    mimetype=proxy_mimetype
                )
                self.db.add(new_binary)
            
            self.db.commit()
            logger.info(f"Successfully updated proxy for {object_key}")
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating proxy for {object_key}: {e}")
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

    def get_all(self, limit: int = 100, offset: int = 0) -> List[MediaObjectRecord]:
        """Retrieves a paginated list of all MediaObjectRecords."""
        try:
            logger.debug(
                f"Querying for all MediaObjects with limit={limit}, offset={offset}"
            )
            orm_objs = (
                self.db.query(ORMMediaObject)
                .options(defer(ORMMediaObject.proxy))  # type: ignore[arg-type]
                .options(defer(ORMMediaObject.thumbnail))  # type: ignore[arg-type]
                .order_by(ORMMediaObject.created_at)
                .offset(offset)
                .limit(limit)
                .all()
            )
            records = [MediaObjectRecord.from_orm(obj, load_binary_fields=False) for obj in orm_objs]
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

    def count(self) -> int:
        """Returns the total count of MediaObjectRecords in the database."""
        try:
            logger.debug("Querying for total count of MediaObjects.")
            total = self.db.query(ORMMediaObject).count()
            logger.debug(f"Total count: {total}")
            return total
        except SQLAlchemyError as e:
            logger.error(f"Database error counting MediaObjects: {e}")
            return 0
    
    def get_adjacent(self, id) -> tuple[Optional[MediaObjectRecord], Optional[MediaObjectRecord]]:
        """Gets the previous and next MediaObjectRecords relative to the given id.
        
        Returns a tuple of (previous, next) MediaObjectRecords.
        Either or both may be None if at the beginning/end of the collection.
        """
        try:
            # Get the current media object to find its position
            current = self.db.query(ORMMediaObject).filter_by(id=id).first()
            if not current:
                return (None, None)
            
            # Get the previous media object (most recent one before current)
            previous_obj = (
                self.db.query(ORMMediaObject)
                .options(defer(ORMMediaObject.proxy))  # type: ignore[arg-type]
                .options(defer(ORMMediaObject.thumbnail))  # type: ignore[arg-type]
                .filter(ORMMediaObject.created_at < current.created_at)
                .order_by(ORMMediaObject.created_at.desc())
                .first()
            )
            
            # Get the next media object (earliest one after current)
            next_obj = (
                self.db.query(ORMMediaObject)
                .options(defer(ORMMediaObject.proxy))  # type: ignore[arg-type]
                .options(defer(ORMMediaObject.thumbnail))  # type: ignore[arg-type]
                .filter(ORMMediaObject.created_at > current.created_at)
                .order_by(ORMMediaObject.created_at)
                .first()
            )
            
            # Convert to domain objects (skip binary fields for performance)
            previous = MediaObjectRecord.from_orm(previous_obj, load_binary_fields=False) if previous_obj else None
            next = MediaObjectRecord.from_orm(next_obj, load_binary_fields=False) if next_obj else None
            
            return (previous, next)
        except SQLAlchemyError as e:
            logger.error(f"Database error getting adjacent MediaObjects for id {id}: {e}")
            return (None, None)
    
    def get_thumbnail(self, media_object_id) -> Optional[tuple[bytes, str]]:
        """Get thumbnail binary data for a media object.
        
        Returns:
            Tuple of (data, mimetype) if found, None otherwise.
        """
        try:
            binary = (
                self.db.query(ORMMediaBinary)
                .filter_by(media_object_id=media_object_id, type=MediaBinaryType.THUMBNAIL)
                .first()
            )
            if binary:
                return (binary.data, binary.mimetype)  # type: ignore[return-value]
            return None
        except SQLAlchemyError as e:
            logger.error(f"Database error getting thumbnail for {media_object_id}: {e}")
            return None
    
    def get_proxy(self, media_object_id) -> Optional[tuple[bytes, str]]:
        """Get proxy binary data for a media object.
        
        Returns:
            Tuple of (data, mimetype) if found, None otherwise.
        """
        try:
            binary = (
                self.db.query(ORMMediaBinary)
                .filter_by(media_object_id=media_object_id, type=MediaBinaryType.PROXY)
                .first()
            )
            if binary:
                return (binary.data, binary.mimetype)  # type: ignore[return-value]
            return None
        except SQLAlchemyError as e:
            logger.error(f"Database error getting proxy for {media_object_id}: {e}")
            return None