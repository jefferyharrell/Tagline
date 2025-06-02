import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import declarative_base, relationship

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

    # Relationship to binaries
    binaries = relationship(
        "ORMMediaBinary", back_populates="media_object", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<OrmMediaObject(object_key={self.object_key}, status={self.ingestion_status})>"


class ORMMediaBinary(Base):
    __tablename__ = "media_binaries"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    media_object_key = Column(
        String(255),
        ForeignKey("media_objects.object_key", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(String(20), nullable=False)  # 'thumbnail' or 'proxy'
    s3_key = Column(String(255), nullable=False, index=True)
    size = Column(Integer, nullable=True)
    mimetype = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship back to media object
    media_object = relationship("ORMMediaObject", back_populates="binaries")

    # Unique constraint to prevent duplicate types per media object
    __table_args__ = (
        UniqueConstraint("media_object_key", "type", name="uq_media_object_type"),
    )

    def __repr__(self):
        return f"<ORMMediaBinary(id={self.id}, media_object_key={self.media_object_key}, type={self.type})>"
