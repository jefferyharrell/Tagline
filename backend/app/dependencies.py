from typing import Annotated, Optional

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.database import get_db
from app.db.repositories.media_object import MediaObjectRepository
from app.s3_binary_storage import S3BinaryStorage, S3Config


def get_media_object_repository(
    db: Annotated[Session, Depends(get_db)]
) -> MediaObjectRepository:
    """
    Dependency-injected MediaObjectRepository for use in routes and background tasks.
    """
    return MediaObjectRepository(db)


# Singleton instance of S3BinaryStorage
_s3_storage: Optional[S3BinaryStorage] = None


def get_s3_binary_storage() -> S3BinaryStorage:
    """
    Get S3BinaryStorage instance for storing thumbnails and proxies.
    Uses singleton pattern to reuse the same S3 client across requests.
    """
    global _s3_storage

    if _s3_storage is None:
        settings = get_settings()

        # Validate S3 configuration
        if not all(
            [
                settings.S3_ENDPOINT_URL,
                settings.S3_ACCESS_KEY_ID,
                settings.S3_SECRET_ACCESS_KEY,
                settings.S3_BUCKET_NAME,
            ]
        ):
            raise HTTPException(
                status_code=500,
                detail="S3 configuration is incomplete. Please check environment variables.",
            )

        # Type assertions - we've already validated these are not None
        config = S3Config(
            endpoint_url=settings.S3_ENDPOINT_URL,  # type: ignore[arg-type]
            access_key_id=settings.S3_ACCESS_KEY_ID,  # type: ignore[arg-type]
            secret_access_key=settings.S3_SECRET_ACCESS_KEY,  # type: ignore[arg-type]
            bucket_name=settings.S3_BUCKET_NAME,  # type: ignore[arg-type]
            region=settings.S3_REGION,
        )

        _s3_storage = S3BinaryStorage(config)

    return _s3_storage
