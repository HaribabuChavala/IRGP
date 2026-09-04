import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = "sqlite:///./test_org_portal_service.db"

from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from app.security import create_access_token

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def org_admin_headers():
    token = create_access_token("org-admin", {"roles": ["ORG_ADMIN"], "organization_id": "org-123"})
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_endpoint_returns_metrics():
    response = client.get("/api/v1/organizations/org-123/dashboard", headers=org_admin_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["organization_id"] == "org-123"
    assert body["data_source_count"] >= 0


def test_data_sources_endpoint_lists_sources():
    response = client.get("/api/v1/organizations/org-123/data-sources", headers=org_admin_headers())
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["data_sources"], list)


def test_org_portal_requires_org_admin_role():
    response = client.get("/api/v1/organizations/org-123/dashboard")
    assert response.status_code == 403
