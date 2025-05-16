import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.unit
def test_health_check():
    client = TestClient(app)
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
