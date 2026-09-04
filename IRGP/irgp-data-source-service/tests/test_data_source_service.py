import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = "sqlite:///./test_data_source_service.db"

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


def test_list_data_sources_for_org():
    response = client.get("/api/v1/data-sources?organization_id=org-123", headers=org_admin_headers("org-123"))
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["data_sources"], list)


def test_create_data_source():
    response = client.post(
        "/api/v1/data-sources",
        json={
            "organization_id": "org-123",
            "name": "Sales Database",
            "type": "postgres",
            "connection_string": "postgresql://user:pass@host:5432/db",
        },
        headers=org_admin_headers("org-123"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["organization_id"] == "org-123"
    assert body["name"] == "Sales Database"


def test_data_source_endpoints_require_org_admin():
    response = client.get("/api/v1/data-sources?organization_id=org-123")
    assert response.status_code == 403
