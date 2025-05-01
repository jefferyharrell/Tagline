import logging
import os
from enum import Enum
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageProviderType(str, Enum):
    FILESYSTEM = "filesystem"
    DROPBOX = "dropbox"
    # Add more providers as needed


class Settings(BaseSettings):
    API_KEY: str
    LOG_LEVEL: int = logging.INFO
    DATABASE_URL: str
    UNIT_TEST_DATABASE_URL: str | None = None  # Optional, for unit tests

    # Storage Provider Configuration
    STORAGE_PROVIDER: StorageProviderType
    FILESYSTEM_ROOT_PATH: str | None = None

    # Dropbox Storage Provider Configuration
    DROPBOX_APP_KEY: str | None = None
    DROPBOX_APP_SECRET: str | None = None
    DROPBOX_REFRESH_TOKEN: str | None = None
    DROPBOX_ROOT_PATH: str | None = None

    @field_validator("STORAGE_PROVIDER", mode="before")
    @classmethod
    def parse_storage_provider(
        cls, v: str | StorageProviderType
    ) -> StorageProviderType:
        if isinstance(v, StorageProviderType):
            return v
        if isinstance(v, str):
            try:
                return StorageProviderType(v.lower())
            except ValueError:
                raise ValueError(f"Invalid STORAGE_PROVIDER: {v}")
        raise ValueError(
            f"STORAGE_PROVIDER must be a string or StorageProviderType, got {type(v)}"
        )

    def get_active_database_url(self) -> str:
        """
        Returns the correct database URL for the current context.
        - If running under pytest (unit test) and UNIT_TEST_DATABASE_URL is set, use it.
        - Otherwise, use DATABASE_URL.
        """
        if os.environ.get("PYTEST_CURRENT_TEST") and self.UNIT_TEST_DATABASE_URL:
            return self.UNIT_TEST_DATABASE_URL
        return self.DATABASE_URL

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def parse_log_level(cls, v: Any) -> int:
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            # Accepts 'INFO', 'DEBUG', etc. (case-insensitive)
            level = logging.getLevelName(v.upper())
            if isinstance(level, int):
                return level
            raise ValueError(f"Invalid log level: {v}")
        raise ValueError(f"LOG_LEVEL must be int or str, got {type(v)}")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="forbid"
    )


def get_settings() -> Settings:
    """
    Returns a fresh Settings instance, reading environment variables at call time.
    This pattern is preferred for testability: tests can patch os.environ or use monkeypatch
    before calling get_settings(), ensuring the correct config is loaded.
    """
    return Settings()  # type: ignore[call-arg]
