import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = "sqlite:///./test_export_service.db"

from fastapi.testclient import TestClient

from app.main import app
from app.security import create_access_token

client = TestClient(app)


def org_admin_headers(organization_id: str):
    token = create_access_token("org-admin", {"roles": ["ORG_ADMIN"], "organization_id": organization_id})
    return {"Authorization": f"Bearer {token}"}


def test_list_exports_for_org():
    response = client.get("/api/v1/exports?organization_id=org-123", headers=org_admin_headers("org-123"))
    assert response.status_code == 200
    assert isinstance(response.json()["exports"], list)


def test_create_export():
    response = client.post(
        "/api/v1/exports",
        json={
            "organization_id": "org-123",
            "report_id": "report-1",
            "format": "pdf",
        },
        headers=org_admin_headers("org-123"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["organization_id"] == "org-123"
    assert body["format"] == "pdf"


def test_export_requires_org_admin():
    response = client.get("/api/v1/exports?organization_id=org-123")
    assert response.status_code == 403
