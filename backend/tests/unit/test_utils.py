"""Test utilities for SQLAlchemy and other test-specific functionality."""

import json
from typing import Any, cast

from sqlalchemy import String, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB as PostgresJSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.type_api import TypeEngine


class JSONBSQLite(TypeDecorator):
    """
    SQLite-compatible JSONB type.

    This type is used to emulate PostgreSQL's JSONB type in SQLite for testing.
    """

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PostgresJSONB())
        else:
            return dialect.type_descriptor(cast(TypeEngine, self.impl))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.loads(value)


# Create a test base class that uses our custom types
TestBase = declarative_base()


# Function to patch SQLAlchemy types for testing
def patch_sqlalchemy_types():
    """
    Patch SQLAlchemy types to work with SQLite for testing.

    This function should be called before creating the test database engine.
    """
    # Register the JSONB type with SQLite dialect
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

    # Monkey patch the SQLiteTypeCompiler class
    # We need to use setattr to avoid type checking issues
    if not hasattr(SQLiteTypeCompiler, "visit_JSONB"):

        def visit_jsonb(self: Any, type_: Any, **kw: Any) -> str:
            # Convert JSONB to TEXT for SQLite
            return "TEXT"

        setattr(SQLiteTypeCompiler, "visit_JSONB", visit_jsonb)

    # Also patch the JSON type if needed
    if not hasattr(SQLiteTypeCompiler, "visit_JSON"):

        def visit_json(self: Any, type_: Any, **kw: Any) -> str:
            # Convert JSON to TEXT for SQLite
            return "TEXT"

        setattr(SQLiteTypeCompiler, "visit_JSON", visit_json)

    return True
