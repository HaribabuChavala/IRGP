import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = "sqlite:///./test_observability_service.db"

from fastapi.testclient import TestClient

from app.main import app
from app.security import create_access_token

client = TestClient(app)


def platform_admin_headers():
    token = create_access_token("platform-admin", {"roles": ["PLATFORM_ADMIN"], "organization_id": "platform"})
    return {"Authorization": f"Bearer {token}"}


def test_list_events():
    response = client.get("/api/v1/observability/events", headers=platform_admin_headers())
    assert response.status_code == 200
    assert isinstance(response.json()["events"], list)


def test_create_event():
    response = client.post(
        "/api/v1/observability/events",
        json={
            "service_name": "report-generation",
            "level": "INFO",
            "message": "report job started",
            "details": {"job_id": "job-123"},
        },
        headers=platform_admin_headers(),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["service_name"] == "report-generation"


def test_observability_requires_platform_admin():
    response = client.get("/api/v1/observability/events")
    assert response.status_code == 403
