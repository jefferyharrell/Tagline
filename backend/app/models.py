import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class MediaBinaryType(str, Enum):
    """Enum for media binary types."""
    THUMBNAIL = "thumbnail"
    PROXY = "proxy"


class ORMMediaObject(Base):
    __tablename__ = "media_objects"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    object_key = Column(String(255), unique=True, nullable=False)
    object_metadata = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationship to binaries
    binaries = relationship("ORMMediaBinary", back_populates="media_object", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<OrmMediaObject(id={self.id}, object_key={self.object_key})>"


class ORMMediaBinary(Base):
    __tablename__ = "media_binaries"
    
    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    media_object_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("media_objects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(String(20), nullable=False)  # 'thumbnail' or 'proxy'
    data = Column(LargeBinary, nullable=False)
    mimetype = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship back to media object
    media_object = relationship("ORMMediaObject", back_populates="binaries")
    
    # Unique constraint to prevent duplicate types per media object
    __table_args__ = (
        UniqueConstraint('media_object_id', 'type', name='uq_media_object_type'),
    )
    
    def __repr__(self):
        return f"<ORMMediaBinary(id={self.id}, media_object_id={self.media_object_id}, type={self.type})>"
