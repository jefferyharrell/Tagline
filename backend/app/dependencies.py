from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.repositories.media_object import MediaObjectRepository


def get_media_object_repository(
    db: Annotated[Session, Depends(get_db)]
) -> MediaObjectRepository:
    """
    Dependency-injected MediaObjectRepository for use in routes and background tasks.
    """
    return MediaObjectRepository(db)