import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = "sqlite:///./test_org_service.db"

from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from app.security import create_access_token

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def admin_headers():
    token = create_access_token("platform-admin", {"roles": ["PLATFORM_ADMIN"]})
    return {"Authorization": f"Bearer {token}"}


def test_create_and_get_organization():
    response = client.post(
        "/api/v1/admin/organizations",
        json={"name": "Acme Labs", "contact_email": "ops@acme.example", "region": "us-east-1", "plan": "pro"},
        headers=admin_headers(),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Acme Labs"
    assert body["plan"] == "pro"

    org_id = body["id"]
    fetched = client.get(f"/api/v1/admin/organizations/{org_id}", headers=admin_headers())
    assert fetched.status_code == 200
    assert fetched.json()["contact_email"] == "ops@acme.example"


def test_list_organizations_filters_by_name():
    client.post(
        "/api/v1/admin/organizations",
        json={"name": "Northwind", "contact_email": "hello@northwind.example", "region": "eu-west-1", "plan": "free"},
        headers=admin_headers(),
    )
    client.post(
        "/api/v1/admin/organizations",
        json={"name": "Acme Health", "contact_email": "ops@acme-health.example", "region": "us-west-2", "plan": "enterprise"},
        headers=admin_headers(),
    )

    response = client.get("/api/v1/admin/organizations?query=acme", headers=admin_headers())
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["name"] == "Acme Health"


def test_org_endpoints_require_platform_admin():
    response = client.get("/api/v1/admin/organizations")
    assert response.status_code == 403


def test_onboard_organization_with_temp_password_invites():
    response = client.post(
        "/api/v1/admin/organizations/onboard",
        json={
            "organization_name": "Acme Labs",
            "contact_email": "ops@acme.example",
            "region": "us-east-1",
            "plan": "pro",
            "organization_admin": {
                "email": "admin@acme.example",
                "username": "acme-admin",
                "full_name": "Acme Admin",
                "role": "ORG_ADMIN",
            },
            "users": [
                {
                    "email": "reporter@acme.example",
                    "username": "reporter",
                    "full_name": "Report User",
                    "role": "REPORT_USER",
                }
            ],
        },
        headers=admin_headers(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["organization"]["name"] == "Acme Labs"
    assert body["email_delivery"] in {"queued", "sent"}
    assert body["created_users"][0]["temporary_password"]
    assert body["created_users"][0]["force_password_reset"] is True
