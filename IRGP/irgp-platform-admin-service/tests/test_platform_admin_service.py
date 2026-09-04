import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.main import app
from app.security import create_access_token

client = TestClient(app)


def platform_admin_headers():
    token = create_access_token("platform-admin", {"roles": ["PLATFORM_ADMIN"], "organization_id": "platform"})
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_requires_platform_admin():
    response = client.get("/api/v1/admin/dashboard")
    assert response.status_code == 403


def test_dashboard_returns_stats():
    response = client.get("/api/v1/admin/dashboard", headers=platform_admin_headers())
    assert response.status_code == 200
    assert isinstance(response.json()["stats"], dict)


def test_platform_stats_returns_summary():
    response = client.get("/api/v1/admin/platform/stats", headers=platform_admin_headers())
    assert response.status_code == 200
    assert isinstance(response.json()["stats"], dict)
