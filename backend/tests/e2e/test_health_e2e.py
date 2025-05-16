import os

import httpx
import pytest
from dotenv import load_dotenv

pytestmark = pytest.mark.e2e

# Load environment variables from .env at the project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

BASE_URL = "http://localhost:8000"


def test_health_e2e():
    response = httpx.get(f"{BASE_URL}/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
