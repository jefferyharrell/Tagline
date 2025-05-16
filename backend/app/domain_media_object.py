"""Domain model for MediaObjectRecord.

This model represents the business logic layer for media objects, decoupled from persistence (ORM) and transport (Pydantic) representations.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from app.models import ORMMediaObject
from app.schemas import MediaObject as PydanticMediaObject, StoredMediaObject


class MediaObjectRecord:
    def __init__(
        self,
        id: Optional[UUID],
        object_key: Optional[str],
        metadata: Dict[str, Any],
        thumbnail: Optional[bytes] = None,
        thumbnail_mimetype: Optional[str] = None,
        proxy: Optional[bytes] = None,
        proxy_mimetype: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        last_modified: Optional[str] = None,
    ):
        self.id = id
        self.object_key = object_key
        self.metadata = metadata
        self.thumbnail = thumbnail
        self.thumbnail_mimetype = thumbnail_mimetype
        self.proxy = proxy
        self.proxy_mimetype = proxy_mimetype
        self.created_at = created_at
        self.updated_at = updated_at
        self.last_modified = last_modified

    @classmethod
    def from_orm(cls, orm_obj: ORMMediaObject) -> "MediaObjectRecord":
        return cls(
            id=getattr(orm_obj, "id", None),
            object_key=getattr(orm_obj, "object_key", None),
            metadata=getattr(orm_obj, "object_metadata", {}) or {},
            thumbnail=getattr(orm_obj, "thumbnail", None),
            thumbnail_mimetype=getattr(orm_obj, "thumbnail_mimetype", None),
            proxy=getattr(orm_obj, "proxy", None),
            proxy_mimetype=getattr(orm_obj, "proxy_mimetype", None),
            created_at=getattr(orm_obj, "created_at", None),
            updated_at=getattr(orm_obj, "updated_at", None),
            last_modified=None,  # Could be derived from updated_at or metadata
        )

    def to_orm(self) -> ORMMediaObject:
        return ORMMediaObject(
            id=self.id,
            object_key=self.object_key,
            object_metadata=self.metadata,
            thumbnail=self.thumbnail,
            thumbnail_mimetype=self.thumbnail_mimetype,
            proxy=self.proxy,
            proxy_mimetype=self.proxy_mimetype,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_pydantic(cls, pydantic_obj: PydanticMediaObject) -> "MediaObjectRecord":
        return cls(
            id=getattr(pydantic_obj, "id", None),
            object_key=pydantic_obj.object_key,
            metadata=pydantic_obj.metadata or {},
            thumbnail=getattr(pydantic_obj, "thumbnail", None),
            thumbnail_mimetype=getattr(pydantic_obj, "thumbnail_mimetype", None),
            proxy=getattr(pydantic_obj, "proxy", b""),
            proxy_mimetype=getattr(pydantic_obj, "proxy_mimetype", None),
            last_modified=getattr(pydantic_obj, "last_modified", None),
        )

    @classmethod
    def from_stored(cls, stored_obj: StoredMediaObject) -> "MediaObjectRecord":
        return cls(
            id=None,  # Not persisted yet
            object_key=stored_obj.object_key,
            metadata=stored_obj.metadata or {},
            thumbnail=getattr(stored_obj, "thumbnail", None),
            thumbnail_mimetype=getattr(stored_obj, "thumbnail_mimetype", None),
            proxy=getattr(stored_obj, "proxy", b""),
            proxy_mimetype=getattr(stored_obj, "proxy_mimetype", None),
            last_modified=getattr(stored_obj, "last_modified", None),
        )

    def to_pydantic(self) -> PydanticMediaObject:
        """Converts this domain object to its Pydantic schema representation."""
        if self.object_key is None:
            raise ValueError(
                "object_key must not be None when converting to PydanticMediaObject"
            )
        if self.id is None:
            raise ValueError(
                "id must not be None when converting to PydanticMediaObject"
            )
        return PydanticMediaObject(
            id=self.id,
            object_key=self.object_key,
            metadata=self.metadata,
            last_modified=self.last_modified,
        )
