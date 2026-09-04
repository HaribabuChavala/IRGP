import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = "sqlite:///./test_auth_service.db"

from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app


client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_register_and_login():
    register_payload = {
        "email": "alice@example.com",
        "username": "alice",
        "password": "StrongPass123",
        "roles": ["REPORT_USER"],
    }

    register_response = client.post("/api/v1/auth/register", json=register_payload)
    assert register_response.status_code == 201
    assert register_response.json()["email"] == "alice@example.com"

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "StrongPass123"},
    )
    assert login_response.status_code == 200
    payload = login_response.json()
    assert payload["access_token"]
    assert payload["refresh_token"]


def test_me_requires_valid_jwt():
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "bob@example.com",
            "username": "bob",
            "password": "StrongPass123",
            "roles": ["REPORT_ADMIN"],
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "StrongPass123"},
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    body = me_response.json()
    assert body["email"] == "bob@example.com"
    assert "REPORT_ADMIN" in body["roles"]


def test_refresh_token_endpoint():
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "charlie@example.com",
            "username": "charlie",
            "password": "StrongPass123",
            "roles": ["VIEWER"],
        },
    )

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "charlie@example.com", "password": "StrongPass123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 200
    body = refresh_response.json()
    assert body["access_token"]
    assert body["refresh_token"]


def test_platform_admin_onboards_organization_and_force_password_reset():
    platform_login = client.post(
        "/api/v1/auth/register",
        json={
            "email": "platform@example.com",
            "username": "platform-admin",
            "password": "StrongPass123",
            "roles": ["PLATFORM_ADMIN"],
        },
    )
    assert platform_login.status_code == 201

    platform_token = client.post(
        "/api/v1/auth/login",
        json={"email": "platform@example.com", "password": "StrongPass123"},
    ).json()["access_token"]

    onboarding = client.post(
        "/api/v1/auth/admin/onboard-organization",
        headers={"Authorization": f"Bearer {platform_token}"},
        json={
            "organization_name": "Acme Labs",
            "contact_email": "ops@acme.com",
            "region": "us-east-1",
            "plan": "pro",
            "organization_admin": {
                "email": "admin@acme.com",
                "username": "acme-admin",
                "full_name": "Acme Admin",
                "role": "ORG_ADMIN",
            },
            "users": [
                {
                    "email": "reporter@acme.com",
                    "username": "reporter",
                    "full_name": "Report User",
                    "role": "REPORT_USER",
                }
            ],
        },
    )

    assert onboarding.status_code == 201
    body = onboarding.json()
    assert body["organization"]["name"] == "Acme Labs"
    assert body["created_users"][0]["force_password_reset"] is True
    assert len(body["created_users"][0]["temporary_password"]) >= 12
    assert body["email_delivery"] == "queued"

    temp_password = body["created_users"][0]["temporary_password"]

    first_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.com", "password": temp_password},
    )
    assert first_login.status_code == 200
    admin_token = first_login.json()["access_token"]

    reset = client.post(
        "/api/v1/auth/reset-password",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"current_password": temp_password, "new_password": "NewStrongPass456"},
    )
    assert reset.status_code == 200
    assert reset.json()["force_password_reset"] is False

    after_reset_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.com", "password": "NewStrongPass456"},
    )
    assert after_reset_login.status_code == 200

    user_lookup = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {after_reset_login.json()['access_token']}"},
    )
    assert user_lookup.status_code == 200
    assert user_lookup.json()["email"] == "admin@acme.com"
