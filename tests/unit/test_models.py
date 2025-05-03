import uuid
from datetime import UTC, datetime
from typing import Any, Dict

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import Base, OrmMediaObject

pytestmark = pytest.mark.unit

# Load environment variables from .env file
load_dotenv()


@pytest.fixture
def fake_metadata() -> Dict[str, Any]:
    return {"description": "Test", "keywords": ["foo", "bar"]}


@pytest.fixture
def db_session():
    # Use the correct database URL for the context (unit/E2E)
    settings = get_settings()
    database_url = settings.get_active_database_url()
    if not database_url:
        pytest.skip("No database URL available for this test context")

    # Create a test-specific schema to avoid conflicts
    test_schema = f"test_{uuid.uuid4().hex[:8]}"
    engine = create_engine(database_url)

    # Create schema and set search path
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {test_schema}"))
        conn.execute(text(f"SET search_path TO {test_schema}"))
        conn.commit()

    # Create tables in test schema
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop the test schema and all its tables
        with engine.connect() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {test_schema} CASCADE"))
            conn.commit()


@pytest.fixture
def media_object(fake_metadata: Dict[str, Any], db_session: Session) -> OrmMediaObject:
    obj = OrmMediaObject(
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


def test_media_object_instantiation(media_object: OrmMediaObject) -> None:
    # Tell pyright these are regular Python attributes, not SQLAlchemy columns
    obj_key: str = media_object.object_key  # type: ignore
    obj_metadata: Dict[str, Any] = media_object.object_metadata  # type: ignore
    created: datetime = media_object.created_at  # type: ignore
    updated: datetime = media_object.updated_at  # type: ignore

    assert obj_key == "test_key"
    assert obj_metadata["description"] == "Test"
    assert isinstance(created, datetime)
    assert isinstance(updated, datetime)


def test_media_object_repr(media_object: OrmMediaObject) -> None:
    # Get the string representation
    obj_key: str = media_object.object_key  # type: ignore
    r = repr(media_object)
    assert "MediaObject" in r
    assert obj_key in r


def test_model_table_and_columns() -> None:
    # Table name is a class attribute, not a column
    assert OrmMediaObject.__tablename__ == "media_objects"
    # Get column names from table definition
    columns = {col.name for col in OrmMediaObject.__table__.columns}
    assert {"id", "object_key", "object_metadata", "created_at", "updated_at"}.issubset(
        columns
    )
