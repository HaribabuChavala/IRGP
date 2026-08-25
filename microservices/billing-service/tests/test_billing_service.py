import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = "sqlite:///./test_billing_service.db"

from fastapi.testclient import TestClient

from app.main import app
from app.security import create_access_token

client = TestClient(app)


def platform_admin_headers():
    token = create_access_token("platform-admin", {"roles": ["PLATFORM_ADMIN"], "organization_id": "platform"})
    return {"Authorization": f"Bearer {token}"}


def test_list_invoices():
    response = client.get("/api/v1/billing/invoices?organization_id=org-123", headers=platform_admin_headers())
    assert response.status_code == 200
    assert isinstance(response.json()["invoices"], list)


def test_create_invoice():
    response = client.post(
        "/api/v1/billing/invoices",
        json={
            "organization_id": "org-123",
            "amount": 99.00,
            "currency": "USD",
            "status": "pending",
        },
        headers=platform_admin_headers(),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["organization_id"] == "org-123"
    assert body["currency"] == "USD"


def test_billing_requires_platform_admin():
    response = client.get("/api/v1/billing/invoices?organization_id=org-123")
    assert response.status_code == 403
