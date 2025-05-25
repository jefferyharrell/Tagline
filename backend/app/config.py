import logging
import os
import sys
from enum import Enum
from typing import Any, List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)


class StorageProviderType(str, Enum):
    FILESYSTEM = "filesystem"
    DROPBOX = "dropbox"
    # Add more providers as needed


class Settings(BaseSettings):
    BACKEND_API_KEY: str
    LOG_LEVEL: int = logging.INFO
    DATABASE_URL: str
    UNIT_TEST_DATABASE_URL: str | None = None  # Optional, for unit tests

    # JWT settings
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"

    # Stytch configuration
    STYTCH_PROJECT_ID: str
    STYTCH_SECRET: str
    STYTCH_ENV: str = "test"  # "test" or "live"

    # Administrator access
    ADMINISTRATOR_EMAIL: str | None = None  # Email that always has access
    
    # Authentication bypass for development
    ENV_MODE: str = "production"  # 'production', 'development', or 'test'
    AUTH_BYPASS_EMAILS: str | None = None  # Comma-separated list of emails that can bypass auth
    AUTH_BYPASS_ENABLED: str | None = None  # Set to 'true' to enable auth bypass
    
    THUMBNAIL_FORMAT: str = "jpeg"
    THUMBNAIL_QUALITY: int = 85
    THUMBNAIL_SIZE: tuple[int, int] = (512, 512)

    PROXY_FORMAT: str = "jpeg"
    PROXY_QUALITY: int = 85
    PROXY_SIZE: tuple[int, int] = (2048, 2048)

    @field_validator("THUMBNAIL_SIZE", mode="before")
    @classmethod
    def parse_thumbnail_size(cls, v):
        if isinstance(v, str):
            # Accept "512,512" or "512x512" or "(512, 512)"
            v = v.strip().replace("x", ",").replace("(", "").replace(")", "")
            parts = [int(part) for part in v.split(",") if part.strip()]
            if len(parts) == 2:
                return tuple(parts)
            raise ValueError("THUMBNAIL_SIZE must be a tuple of two integers")
        if isinstance(v, (list, tuple)) and len(v) == 2:
            return tuple(map(int, v))
        if isinstance(v, int):
            return (v, v)
        raise ValueError("THUMBNAIL_SIZE must be a tuple of two integers")

    @field_validator("PROXY_SIZE", mode="before")
    @classmethod
    def parse_proxy_size(cls, v):
        if isinstance(v, str):
            try:
                width, height = map(int, v.split("x"))
                return (width, height)
            except ValueError:
                pass
        elif (
            isinstance(v, tuple) and len(v) == 2 and all(isinstance(i, int) for i in v)
        ):
            return v
        raise ValueError(
            'PROXY_SIZE must be a tuple of two integers or a string like "1024x1024"'
        )

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
