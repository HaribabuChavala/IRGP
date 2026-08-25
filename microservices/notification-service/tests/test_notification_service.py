import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = "sqlite:///./test_notification_service.db"

from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from app.security import create_access_token

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def org_admin_headers(organization_id: str):
    token = create_access_token("org-admin", {"roles": ["ORG_ADMIN"], "organization_id": organization_id})
    return {"Authorization": f"Bearer {token}"}


def test_get_notifications_for_org():
    response = client.get("/api/v1/notifications?organization_id=org-123", headers=org_admin_headers("org-123"))
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["notifications"], list)


def test_create_notification():
    response = client.post(
        "/api/v1/notifications",
        json={"organization_id": "org-123", "message": "Report generated", "type": "INFO"},
        headers=org_admin_headers("org-123"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["organization_id"] == "org-123"
    assert body["message"] == "Report generated"


def test_notifications_require_org_admin():
    response = client.get("/api/v1/notifications?organization_id=org-123")
    assert response.status_code == 403
