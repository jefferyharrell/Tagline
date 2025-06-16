from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MediaBinaryType(str, Enum):
    """Enum for media binary types."""

    THUMBNAIL = "thumbnail"
    PROXY = "proxy"


class IngestionStatus(str, Enum):
    """Enum for media object ingestion status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ORMMediaObject(Base):
    __tablename__ = "media_objects"

    object_key = Column(String(255), primary_key=True, nullable=False)
    ingestion_status = Column(
        String(20), nullable=False, default=IngestionStatus.PENDING.value, index=True
    )
    object_metadata = Column(
        JSONB, nullable=True, default=dict
    )  # Nullable until ingested
    file_size = Column(Integer, nullable=True)  # Store file size from discovery
    file_mimetype = Column(String(255), nullable=True)  # Store mimetype from discovery
    file_last_modified = Column(
        DateTime, nullable=True
    )  # Store last modified from discovery
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Direct object keys for thumbnails and proxies (replaces media_binaries relationship)
    thumbnail_object_key = Column(String(255), nullable=True)
    proxy_object_key = Column(String(255), nullable=True)

    # Path depth for efficient folder filtering (number of '/' separators + 1)
    path_depth = Column(Integer, nullable=False)
    
    # Move detection fields
    content_hash = Column(String(64), nullable=True, index=True)
    provider_file_id = Column(String(255), nullable=True, index=True)
    provider_metadata = Column(JSONB, nullable=True)
    previous_object_keys = Column(ARRAY(String), nullable=True)
    moved_from = Column(String(255), nullable=True)
    move_detected_at = Column(DateTime, nullable=True)
    is_copy = Column(Boolean, nullable=True, default=False)

    def to_pydantic(self):
        """Convert this ORM object to its Pydantic representation."""
        from app.schemas import MediaObject
        
        return MediaObject(
            object_key=self.object_key,
            ingestion_status=self.ingestion_status,
            file_size=self.file_size,
            file_mimetype=self.file_mimetype,
            file_last_modified=self.file_last_modified,
            created_at=self.created_at,
            updated_at=self.updated_at,
            metadata=self.object_metadata or {},
            has_thumbnail=bool(self.thumbnail_object_key),
            has_proxy=bool(self.proxy_object_key),
            content_hash=self.content_hash,
            provider_file_id=self.provider_file_id,
            provider_metadata=self.provider_metadata,
            previous_object_keys=self.previous_object_keys,
            moved_from=self.moved_from,
            move_detected_at=self.move_detected_at,
            is_copy=self.is_copy,
        )

    def __repr__(self):
        return f"<OrmMediaObject(object_key={self.object_key}, status={self.ingestion_status})>"
