import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def set_test_env_vars():
    # Database settings
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

    # API settings
    os.environ.setdefault("BACKEND_API_KEY", "dummy-api-key")

    # Storage settings
    os.environ.setdefault("STORAGE_PROVIDER", "filesystem")

    # JWT Authentication settings
    os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key")
    os.environ.setdefault("JWT_ALGORITHM", "HS256")

    # Stytch Authentication settings
    os.environ.setdefault("STYTCH_PROJECT_ID", "test-project-id")
    os.environ.setdefault("STYTCH_SECRET", "test-secret-key")
    os.environ.setdefault("STYTCH_ENV", "test")
