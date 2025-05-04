import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


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
    thumbnail = Column(LargeBinary, nullable=True)
    thumbnail_mimetype = Column(String, nullable=True)
    proxy = Column(LargeBinary, nullable=True)
    proxy_mimetype = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<OrmMediaObject(id={self.id}, object_key={self.object_key})>"
