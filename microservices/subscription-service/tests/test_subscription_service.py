import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = "sqlite:///./test_subscription_service.db"

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


def test_list_subscription_plans():
    response = client.get("/api/v1/subscriptions/plans")
    assert response.status_code == 200
    body = response.json()
    assert "plans" in body
    assert "free" in body["plans"]


def test_get_current_subscription_for_org():
    response = client.get(
        "/api/v1/organizations/org-123/subscription",
        headers=org_admin_headers("org-123"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["organization_id"] == "org-123"
    assert body["plan"] in {"free", "pro", "enterprise"}


def test_upgrade_subscription_requires_org_admin():
    response = client.post("/api/v1/organizations/org-123/subscription/upgrade", json={"plan": "pro"})
    assert response.status_code == 403
