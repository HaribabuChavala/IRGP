import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = "sqlite:///./test_audit_service.db"

from fastapi.testclient import TestClient

from app.main import app
from app.security import create_access_token

client = TestClient(app)


def org_admin_headers(organization_id: str):
    token = create_access_token("org-admin", {"roles": ["ORG_ADMIN"], "organization_id": organization_id})
    return {"Authorization": f"Bearer {token}"}


def test_list_audit_events_for_org():
    response = client.get("/api/v1/audit?organization_id=org-123", headers=org_admin_headers("org-123"))
    assert response.status_code == 200
    assert isinstance(response.json()["events"], list)


def test_create_audit_event():
    response = client.post(
        "/api/v1/audit",
        json={
            "organization_id": "org-123",
            "actor_id": "user-1",
            "entity_type": "report",
            "entity_id": "rpt-1",
            "action": "created",
            "details": {"title": "Quarterly Summary"},
        },
        headers=org_admin_headers("org-123"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["organization_id"] == "org-123"
    assert body["action"] == "created"


def test_audit_requires_org_admin():
    response = client.get("/api/v1/audit?organization_id=org-123")
    assert response.status_code == 403
