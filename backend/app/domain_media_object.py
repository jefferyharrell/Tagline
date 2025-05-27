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
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        last_modified: Optional[str] = None,
    ):
        self.id = id
        self.object_key = object_key
        self.metadata = metadata
        self.created_at = created_at
        self.updated_at = updated_at
        self.last_modified = last_modified

    @classmethod
    def from_orm(cls, orm_obj: ORMMediaObject, load_binary_fields: bool = True) -> "MediaObjectRecord":
        """Convert ORM object to domain object.
        
        Args:
            orm_obj: The ORM MediaObject
            load_binary_fields: Deprecated parameter, kept for backward compatibility
        """
        return cls(
            id=getattr(orm_obj, "id", None),
            object_key=getattr(orm_obj, "object_key", None),
            metadata=getattr(orm_obj, "object_metadata", {}) or {},
            created_at=getattr(orm_obj, "created_at", None),
            updated_at=getattr(orm_obj, "updated_at", None),
            last_modified=None,  # Could be derived from updated_at or metadata
        )

    def to_orm(self) -> ORMMediaObject:
        return ORMMediaObject(
            id=self.id,
            object_key=self.object_key,
            object_metadata=self.metadata,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_pydantic(cls, pydantic_obj: PydanticMediaObject) -> "MediaObjectRecord":
        return cls(
            id=getattr(pydantic_obj, "id", None),
            object_key=pydantic_obj.object_key,
            metadata=pydantic_obj.metadata or {},
            last_modified=getattr(pydantic_obj, "last_modified", None),
        )

    @classmethod
    def from_stored(cls, stored_obj: StoredMediaObject) -> "MediaObjectRecord":
        return cls(
            id=None,  # Not persisted yet
            object_key=stored_obj.object_key,
            metadata=stored_obj.metadata or {},
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
