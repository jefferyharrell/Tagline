"""Repository for managing MediaObject persistence."""

import logging
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models import MediaObject as ORM_MediaObject
from app.storage_types import (  # Use Pydantic for input
    MediaObject as PydanticMediaObject,
)

logger = logging.getLogger(__name__)


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

    def get_by_id(self, id) -> Optional[ORM_MediaObject]:
        """Retrieves a MediaObject by its UUID."""
        session = self.SessionLocal()
        try:
            logger.debug(f"Querying for MediaObject with id: {id}")
            media_object = session.query(ORM_MediaObject).filter_by(id=id).first()
            if media_object:
                logger.debug(f"Found MediaObject: {media_object.id}")
            else:
                logger.debug("MediaObject not found for id: %s", id)
            return media_object
        except SQLAlchemyError as e:
            logger.error(f"Database error querying for id {id}: {e}")
            return None
        finally:
            session.close()

    def get_by_object_key(self, object_key: str) -> Optional[ORM_MediaObject]:
        """Retrieves a MediaObject by its object_key."""
        session = self.SessionLocal()
        try:
            logger.debug(f"Querying for MediaObject with object_key: {object_key}")
            media_object = (
                session.query(ORM_MediaObject).filter_by(object_key=object_key).first()
            )
            if media_object:
                logger.debug(f"Found MediaObject: {media_object.id}")
            else:
                logger.debug("MediaObject not found for key: %s", object_key)
            return media_object
        except SQLAlchemyError as e:
            logger.error(f"Database error querying for object_key {object_key}: {e}")
            return None
        finally:
            session.close()

    def create(self, media_object: PydanticMediaObject) -> Optional[ORM_MediaObject]:
        """Creates a new MediaObject record in the database or retrieves existing.

        Attempts to add the new object and commits. If an IntegrityError occurs
        (likely due to the unique constraint on object_key), it rolls back and
        fetches the existing object by object_key.

        Args:
            media_object: The MediaObject schema object containing data.

        Returns:
            The created or existing MediaObjectModel, or None on other errors.
        """
        logger.debug(
            f"Attempting to create/get MediaObject for key: {media_object.object_key}"
        )
        db_obj = ORM_MediaObject(
            object_key=media_object.object_key,
            object_metadata=media_object.metadata or {},
        )
        session = self.SessionLocal()
        try:
            with session.begin_nested():  # Use nested transaction if already in one
                session.add(db_obj)
            # Commit the outer transaction if this is the top level
            session.commit()
            logger.info(
                f"Successfully created MediaObject: {db_obj.id} for key {db_obj.object_key}"
            )
            return db_obj
        except IntegrityError:
            session.rollback()  # Rollback the failed insert
            logger.warning(
                f"IntegrityError on create for key {media_object.object_key}, likely exists. Fetching."
            )
            # Fetch and return the existing object
            existing_obj = self.get_by_object_key(media_object.object_key)
            if existing_obj:
                logger.info(
                    f"Found existing MediaObject: {existing_obj.id} for key {existing_obj.object_key}"
                )
            else:
                # This case is unlikely if IntegrityError was due to object_key, but log it.
                logger.error(
                    f"IntegrityError occurred but failed to fetch existing object for key {media_object.object_key}"
                )
            return existing_obj
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(
                f"Database error creating MediaObject for key {media_object.object_key}: {e}"
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
                session.query(ORM_MediaObject).filter_by(object_key=object_key).first()
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

    def get_or_create(
        self, media_object: PydanticMediaObject
    ) -> Optional[ORM_MediaObject]:
        """Gets an existing MediaObject by object_key or creates it if not found.

        Relies on the atomic nature of the updated create() method.

        Args:
            media_object: The MediaObject schema object.

        Returns:
            The existing or newly created MediaObjectModel, or None on error.
        """
        # The 'create' method now handles the 'get or create' logic atomically
        return self.create(media_object)
