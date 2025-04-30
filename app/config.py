import logging
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    API_KEY: str = "changeme"
    LOG_LEVEL: int = logging.INFO
    DATABASE_URL: str

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
