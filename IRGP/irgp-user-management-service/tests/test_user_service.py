import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = "sqlite:///./test_user_service.db"

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


def test_create_and_get_user():
    response = client.post(
        "/api/v1/admin/users",
        json={
            "email": "alice@example.com",
            "username": "alice",
            "full_name": "Alice Example",
            "organization_id": "org-123",
            "role": "REPORT_ADMIN",
        },
        headers=admin_headers(),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["role"] == "REPORT_ADMIN"

    user_id = body["id"]
    fetched = client.get(f"/api/v1/admin/users/{user_id}", headers=admin_headers())
    assert fetched.status_code == 200
    assert fetched.json()["username"] == "alice"


def test_list_users_filters_by_email():
    client.post(
        "/api/v1/admin/users",
        json={
            "email": "bob@example.com",
            "username": "bob",
            "full_name": "Bob Example",
            "organization_id": "org-456",
            "role": "REPORT_USER",
        },
        headers=admin_headers(),
    )
    client.post(
        "/api/v1/admin/users",
        json={
            "email": "charlie@example.com",
            "username": "charlie",
            "full_name": "Charlie Example",
            "organization_id": "org-456",
            "role": "REPORT_ADMIN",
        },
        headers=admin_headers(),
    )

    response = client.get("/api/v1/admin/users?query=charlie", headers=admin_headers())
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["email"] == "charlie@example.com"


def test_users_require_platform_admin():
    response = client.get("/api/v1/admin/users")
    assert response.status_code == 403
