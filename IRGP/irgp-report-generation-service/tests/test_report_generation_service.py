import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = "sqlite:///./test_report_generation_service.db"

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


def test_generate_report_returns_job_id_and_status():
    response = client.post(
        "/api/v1/reports/generate",
        json={
            "organization_id": "org-123",
            "title": "Revenue Summary",
            "data_source_id": "ds-1",
            "template": "default",
        },
        headers=org_admin_headers("org-123"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] in {"queued", "running", "completed"}
    assert body["organization_id"] == "org-123"


def test_get_report_by_id():
    created = client.post(
        "/api/v1/reports/generate",
        json={
            "organization_id": "org-123",
            "title": "Monthly Overview",
            "data_source_id": "ds-2",
            "template": "default",
        },
        headers=org_admin_headers("org-123"),
    )
    report_id = created.json()["id"]
    response = client.get(f"/api/v1/reports/{report_id}", headers=org_admin_headers("org-123"))
    assert response.status_code == 200
    assert response.json()["title"] == "Monthly Overview"


def test_report_generation_requires_org_admin():
    response = client.post(
        "/api/v1/reports/generate",
        json={
            "organization_id": "org-123",
            "title": "Revenue Summary",
            "data_source_id": "ds-1",
            "template": "default",
        },
    )
    assert response.status_code == 403
