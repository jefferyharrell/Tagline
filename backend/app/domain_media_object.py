"""Domain model for MediaObjectRecord.

This model represents the business logic layer for media objects, decoupled from persistence (ORM) and transport (Pydantic) representations.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from app.models import ORMMediaObject, IngestionStatus
from app.schemas import MediaObject as PydanticMediaObject, StoredMediaObject


class MediaObjectRecord:
    def __init__(
        self,
        object_key: str,
        ingestion_status: str = IngestionStatus.PENDING.value,
        metadata: Optional[Dict[str, Any]] = None,
        file_size: Optional[int] = None,
        file_mimetype: Optional[str] = None,
        file_last_modified: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        has_thumbnail: bool = False,
        has_proxy: bool = False,
    ):
        self.object_key = object_key
        self.ingestion_status = ingestion_status
        self.metadata = metadata or {}
        self.file_size = file_size
        self.file_mimetype = file_mimetype
        self.file_last_modified = file_last_modified
        self.created_at = created_at
        self.updated_at = updated_at
        self.has_thumbnail = has_thumbnail
        self.has_proxy = has_proxy

    @classmethod
    def from_orm(
        cls, orm_obj: ORMMediaObject, load_binary_fields: bool = True
    ) -> "MediaObjectRecord":
        """Convert ORM object to domain object.

        Args:
            orm_obj: The ORM MediaObject
            load_binary_fields: Whether to check for binaries
        """
        # Check if has thumbnail/proxy by looking at binaries relationship
        has_thumbnail = False
        has_proxy = False
        if load_binary_fields and hasattr(orm_obj, 'binaries'):
            for binary in orm_obj.binaries:
                if binary.type == 'thumbnail':
                    has_thumbnail = True
                elif binary.type == 'proxy':
                    has_proxy = True
        
        return cls(
            object_key=getattr(orm_obj, "object_key", ""),
            ingestion_status=getattr(orm_obj, "ingestion_status", IngestionStatus.PENDING.value),
            metadata=getattr(orm_obj, "object_metadata", {}) or {},
            file_size=getattr(orm_obj, "file_size", None),
            file_mimetype=getattr(orm_obj, "file_mimetype", None),
            file_last_modified=getattr(orm_obj, "file_last_modified", None),
            created_at=getattr(orm_obj, "created_at", None),
            updated_at=getattr(orm_obj, "updated_at", None),
            has_thumbnail=has_thumbnail,
            has_proxy=has_proxy,
        )

    def to_orm(self) -> ORMMediaObject:
        return ORMMediaObject(
            object_key=self.object_key,
            ingestion_status=self.ingestion_status,
            object_metadata=self.metadata,
            file_size=self.file_size,
            file_mimetype=self.file_mimetype,
            file_last_modified=self.file_last_modified,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_pydantic(cls, pydantic_obj: PydanticMediaObject) -> "MediaObjectRecord":
        return cls(
            object_key=pydantic_obj.object_key,
            ingestion_status=pydantic_obj.ingestion_status,
            metadata=pydantic_obj.metadata or {},
            file_size=pydantic_obj.file_size,
            file_mimetype=pydantic_obj.file_mimetype,
            file_last_modified=pydantic_obj.file_last_modified,
            created_at=pydantic_obj.created_at,
            updated_at=pydantic_obj.updated_at,
            has_thumbnail=pydantic_obj.has_thumbnail,
            has_proxy=pydantic_obj.has_proxy,
        )

    @classmethod
    def from_stored(cls, stored_obj: StoredMediaObject) -> "MediaObjectRecord":
        # Extract file info from metadata if available
        file_size = None
        file_mimetype = None
        if stored_obj.metadata:
            file_size = stored_obj.metadata.get('size')
            file_mimetype = stored_obj.metadata.get('mimetype')
            
        return cls(
            object_key=stored_obj.object_key,
            ingestion_status=IngestionStatus.PENDING.value,
            metadata=stored_obj.metadata or {},
            file_size=file_size,
            file_mimetype=file_mimetype,
            file_last_modified=datetime.fromisoformat(stored_obj.last_modified) if stored_obj.last_modified else None,
        )

    def to_pydantic(self) -> PydanticMediaObject:
        """Converts this domain object to its Pydantic schema representation."""
        if self.object_key is None:
            raise ValueError(
                "object_key must not be None when converting to PydanticMediaObject"
            )
        return PydanticMediaObject(
            object_key=self.object_key,
            ingestion_status=self.ingestion_status,
            metadata=self.metadata,
            file_size=self.file_size,
            file_mimetype=self.file_mimetype,
            file_last_modified=self.file_last_modified,
            created_at=self.created_at,
            updated_at=self.updated_at,
            has_thumbnail=self.has_thumbnail,
            has_proxy=self.has_proxy,
        )
