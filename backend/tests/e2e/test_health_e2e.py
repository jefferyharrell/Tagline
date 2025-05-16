import os
from contextlib import contextmanager

import httpx
import pytest
from dotenv import load_dotenv

pytestmark = pytest.mark.e2e

# Load environment variables from .env at the project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

BASE_URL = "http://localhost:8000"


@contextmanager
def server_connection():
    """Context manager to handle server connection errors gracefully."""
    try:
        yield
    except (httpx.ConnectError, httpx.ReadError, httpx.ConnectTimeout):
        pytest.skip("Server is not running or not accessible")


def test_health_e2e():
    with server_connection():
        response = httpx.get(f"{BASE_URL}/v1/health", timeout=2.0)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
