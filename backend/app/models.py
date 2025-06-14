from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
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
        String(20), 
        nullable=False, 
        default=IngestionStatus.PENDING.value,
        index=True
    )
    object_metadata = Column(JSONB, nullable=True, default=dict)  # Nullable until ingested
    file_size = Column(Integer, nullable=True)  # Store file size from discovery
    file_mimetype = Column(String(255), nullable=True)  # Store mimetype from discovery
    file_last_modified = Column(DateTime, nullable=True)  # Store last modified from discovery
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Direct object keys for thumbnails and proxies (replaces media_binaries relationship)
    thumbnail_object_key = Column(String(255), nullable=True)
    proxy_object_key = Column(String(255), nullable=True)
    
    # Path depth for efficient folder filtering (number of '/' separators + 1)
    path_depth = Column(Integer, nullable=False)

    def __repr__(self):
        return f"<OrmMediaObject(object_key={self.object_key}, status={self.ingestion_status})>"
