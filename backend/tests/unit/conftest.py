import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def set_test_env_vars():
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("API_KEY", "dummy-api-key")
    os.environ.setdefault("STORAGE_PROVIDER", "filesystem")
    # Add more defaults as your tests require
