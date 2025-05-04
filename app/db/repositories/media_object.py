"""Repository for managing MediaObject persistence."""

import logging
from typing import List, Optional

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.domain_media_object import MediaObjectRecord
from app.models import ORMMediaObject

logger = logging.getLogger(__name__)


class MediaObjectNotFound(Exception):
    """Raised when a MediaObject is not found for update/save."""

    pass


class MediaObjectRepository:
    """Handles database operations for MediaObject models."""

    def __init__(self):
        """Initializes the database connection."""
        settings = get_settings()
        try:
            self.engine = create_engine(settings.DATABASE_URL)
            self.SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine
            )
            logger.debug("MediaObjectRepository initialized successfully.")
        except Exception:
            logger.exception(
                "Failed to initialize MediaObjectRepository database connection."
            )
            # Decide if you want to raise or handle differently
            # For now, let's raise to prevent using a non-functional repository
            raise

    def get_by_id(self, id) -> Optional[MediaObjectRecord]:
        """Retrieves a MediaObjectRecord by its UUID."""
        session = self.SessionLocal()
        try:
            logger.debug(f"Querying for MediaObject with id: {id}")
            orm_obj = session.query(ORMMediaObject).filter_by(id=id).first()
            if orm_obj:
                logger.debug(f"Found MediaObject: {orm_obj.id}")
                return MediaObjectRecord.from_orm(orm_obj)
            else:
                logger.debug("MediaObject not found for id: %s", id)
                return None
        except SQLAlchemyError as e:
            logger.error(f"Database error querying for id {id}: {e}")
            return None
        finally:
            session.close()

    def get_by_object_key(self, object_key: str) -> Optional[MediaObjectRecord]:
        """Retrieves a MediaObjectRecord by its object_key."""
        assert object_key is not None, "object_key must not be None"
        session = self.SessionLocal()
        try:
            logger.debug(f"Querying for MediaObject with object_key: {object_key}")
            orm_obj = (
                session.query(ORMMediaObject).filter_by(object_key=object_key).first()
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
        finally:
            session.close()

    def create(self, record: MediaObjectRecord) -> Optional[MediaObjectRecord]:
        """Creates a new MediaObjectRecord in the database or retrieves existing."""
        assert record.object_key is not None, "object_key must not be None"
        logger.debug(
            f"Attempting to create/get MediaObject for key: {record.object_key}"
        )
        orm_obj = record.to_orm()
        session = self.SessionLocal()
        try:
            with session.begin_nested():
                session.add(orm_obj)
            session.commit()
            logger.info(
                f"Successfully created MediaObject: {orm_obj.id} for key {orm_obj.object_key}"
            )
            return MediaObjectRecord.from_orm(orm_obj)
        except IntegrityError:
            session.rollback()
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
            session.rollback()
            logger.error(
                f"Database error creating MediaObject for key {record.object_key}: {e}"
            )
            return None
        finally:
            session.close()

    def update_thumbnail(
        self, object_key: str, thumbnail_bytes: bytes, thumbnail_mimetype: str
    ) -> bool:
        """Updates the thumbnail and its mimetype for a MediaObject identified by its object_key.

        Args:
            object_key: The unique key of the MediaObject to update.
            thumbnail_bytes: The binary data of the thumbnail.
            thumbnail_mimetype: The mimetype of the thumbnail.

        Returns:
            True if the update was successful, False otherwise.
        """
        session = self.SessionLocal()
        try:
            logger.debug(f"Attempting to update thumbnail for object_key: {object_key}")
            media_object = (
                session.query(ORMMediaObject).filter_by(object_key=object_key).first()
            )
            if not media_object:
                logger.warning(
                    f"MediaObject not found for thumbnail update: {object_key}"
                )
                return False

            media_object.thumbnail = thumbnail_bytes  # type: ignore[assignment] # ORM handles assignment to Column attribute
            media_object.thumbnail_mimetype = thumbnail_mimetype  # type: ignore[assignment] # ORM handles assignment to Column attribute
            session.commit()
            logger.info(f"Successfully updated thumbnail for {object_key}")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error updating thumbnail for {object_key}: {e}")
            return False
        finally:
            session.close()

    def update_proxy(
        self, object_key: str, proxy_bytes: bytes, proxy_mimetype: str
    ) -> bool:
        """Updates the proxy and its mimetype for a MediaObject identified by its object_key.

        Args:
            object_key: The unique key of the MediaObject to update.
            proxy_bytes: The binary data of the proxy.
            proxy_mimetype: The mimetype of the proxy.

        Returns:
            True if the update was successful, False otherwise.
        """
        session = self.SessionLocal()
        try:
            logger.debug(f"Attempting to update proxy for object_key: {object_key}")
            media_object = (
                session.query(ORMMediaObject).filter_by(object_key=object_key).first()
            )
            if not media_object:
                logger.warning(f"MediaObject not found for proxy update: {object_key}")
                return False

            media_object.proxy = proxy_bytes  # type: ignore[assignment]
            media_object.proxy_mimetype = proxy_mimetype  # type: ignore[assignment]
            session.commit()
            logger.info(f"Successfully updated proxy for {object_key}")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error updating proxy for {object_key}: {e}")
            return False
        finally:
            session.close()

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
        session = self.SessionLocal()
        try:
            logger.debug(
                f"Querying for all MediaObjects with limit={limit}, offset={offset}"
            )
            orm_objs = (
                session.query(ORMMediaObject)
                .order_by(ORMMediaObject.created_at)
                .offset(offset)
                .limit(limit)
                .all()
            )
            records = [MediaObjectRecord.from_orm(obj) for obj in orm_objs]
            logger.debug(f"Found {len(records)} MediaObjects.")
            return records
        except SQLAlchemyError as e:
            logger.error(f"Database error querying for all MediaObjects: {e}")
            return []
        finally:
            session.close()

    def save(self, record: MediaObjectRecord) -> MediaObjectRecord:
        """
        Updates an existing MediaObjectRecord in the database.
        Raises MediaObjectNotFound if not found.
        Returns the updated MediaObjectRecord.
        """
        assert record.id is not None, "id must not be None for update/save"
        session = self.SessionLocal()
        try:
            orm_obj = session.query(ORMMediaObject).filter_by(id=record.id).first()
            if orm_obj is None:
                raise MediaObjectNotFound(f"MediaObject with id {record.id} not found.")
            # Update fields
            from typing import cast

            if record.object_key is not None:
                orm_obj.object_key = cast(str, record.object_key)  # type: ignore[assignment]
            if record.metadata is not None:
                orm_obj.object_metadata = cast(dict, record.metadata)  # type: ignore[assignment]
            if record.thumbnail is not None:
                orm_obj.thumbnail = cast(bytes, record.thumbnail)  # type: ignore[assignment]
            if record.thumbnail_mimetype is not None:
                orm_obj.thumbnail_mimetype = cast(str, record.thumbnail_mimetype)  # type: ignore[assignment]
            # updated_at expects a datetime
            from datetime import datetime

            if record.last_modified:
                try:
                    # Try to parse ISO8601 string to datetime
                    new_updated_at = datetime.fromisoformat(record.last_modified)
                    orm_obj.updated_at = new_updated_at  # type: ignore[assignment]
                except Exception:
                    pass  # fallback: do not update if parsing fails
            session.commit()
            return MediaObjectRecord.from_orm(orm_obj)
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def count(self) -> int:
        """Returns the total count of MediaObjectRecords in the database."""
        session = self.SessionLocal()
        try:
            logger.debug("Querying for total count of MediaObjects.")
            total = session.query(ORMMediaObject).count()
            logger.debug(f"Total count: {total}")
            return total
        except SQLAlchemyError as e:
            logger.error(f"Database error counting MediaObjects: {e}")
            return 0
        finally:
            session.close()
