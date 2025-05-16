import uuid
from datetime import UTC, datetime
from typing import Any, Dict

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, ORMMediaObject
from tests.unit.test_utils import patch_sqlalchemy_types

pytestmark = pytest.mark.unit

# Load environment variables from .env file
load_dotenv()


@pytest.fixture
def fake_metadata() -> Dict[str, Any]:
    return {"description": "Test", "keywords": ["foo", "bar"]}


@pytest.fixture
def db_session():
    # Use SQLite in-memory database for unit tests
    engine = create_engine("sqlite:///:memory:")

    # Patch SQLAlchemy types to work with SQLite
    patch_sqlalchemy_types()

    # Register UUID type adapter for SQLite
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

    if not hasattr(SQLiteTypeCompiler, "visit_UUID"):
        SQLiteTypeCompiler.visit_UUID = lambda self, type_, **kw: "VARCHAR(36)"

    # Create all tables in the in-memory database
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        # No need to drop tables for in-memory database as they're automatically
        # removed when the connection is closed


@pytest.fixture
def media_object(fake_metadata: Dict[str, Any], db_session: Session) -> ORMMediaObject:
    obj = ORMMediaObject(
        id=uuid.uuid4(),
        object_key="test_key",
        object_metadata=fake_metadata,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


def test_media_object_instantiation(media_object: ORMMediaObject) -> None:
    # Tell pyright these are regular Python attributes, not SQLAlchemy columns
    obj_key: str = media_object.object_key  # type: ignore
    obj_metadata: Dict[str, Any] = media_object.object_metadata  # type: ignore
    created: datetime = media_object.created_at  # type: ignore
    updated: datetime = media_object.updated_at  # type: ignore

    assert obj_key == "test_key"
    assert obj_metadata["description"] == "Test"
    assert isinstance(created, datetime)
    assert isinstance(updated, datetime)


def test_media_object_repr(media_object: ORMMediaObject) -> None:
    # Get the string representation
    obj_key: str = media_object.object_key  # type: ignore
    r = repr(media_object)
    assert "MediaObject" in r
    assert obj_key in r


def test_model_table_and_columns() -> None:
    # Table name is a class attribute, not a column
    assert ORMMediaObject.__tablename__ == "media_objects"
    # Get column names from table definition
    columns = {col.name for col in ORMMediaObject.__table__.columns}
    assert {"id", "object_key", "object_metadata", "created_at", "updated_at"}.issubset(
        columns
    )
