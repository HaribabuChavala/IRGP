import os
import sys
import time

import requests

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
REALM = os.getenv("KEYCLOAK_REALM", "report-platform")
ADMIN_USERNAME = os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "change-me-admin")

DEFAULT_ATTRIBUTES = {
    "platform-admin": {
        "tenant_id": ["platform"],
        "organization_name": ["Instant Report Platform"],
        "region": ["global"],
    },
    "org-admin": {
        "tenant_id": ["org-acme"],
        "organization_name": ["Acme Financial"],
        "region": ["us-east"],
    },
    "report-user": {
        "tenant_id": ["org-acme"],
        "organization_name": ["Acme Financial"],
        "region": ["us-east"],
    },
    "hari": {
        "tenant_id": ["org-spartexai"],
        "organization_name": ["Spartexai"],
        "region": ["us-east"],
    },
    "alex": {
        "tenant_id": ["org-spartexai"],
        "organization_name": ["Spartexai"],
        "region": ["us-east"],
    },
}


def get_admin_token() -> str:
    url = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"
    response = requests.post(
        url,
        data={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
            "grant_type": "password",
            "client_id": "admin-cli",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_users(token: str):
    url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users"
    response = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=20)
    response.raise_for_status()
    return response.json()


def sync_user(user: dict, token: str) -> bool:
    username = user.get("username")
    attributes = dict(user.get("attributes") or {})
    desired = DEFAULT_ATTRIBUTES.get(username, {})
    if not desired:
        email = (user.get("email") or "").lower()
        for known_username, attrs in DEFAULT_ATTRIBUTES.items():
            if known_username in email:
                desired = attrs
                break

    updated = False
    for key, value in desired.items():
        target = list(value) if isinstance(value, list) else [str(value)]
        if attributes.get(key) != target:
            attributes[key] = target
            updated = True

    if not updated:
        return False

    payload = {
        "enabled": user.get("enabled", True),
        "username": user.get("username"),
        "email": user.get("email"),
        "firstName": user.get("firstName", ""),
        "lastName": user.get("lastName", ""),
        "attributes": attributes,
    }
    if user.get("emailVerified") is not None:
        payload["emailVerified"] = user.get("emailVerified")

    response = requests.put(
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user['id']}",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=20,
    )
    response.raise_for_status()
    print(f"Synced attributes for {username}")
    return True


def main() -> int:
    for _ in range(60):
        try:
            token = get_admin_token()
            users = get_users(token)
            synced = 0
            for user in users:
                if sync_user(user, token):
                    synced += 1
            print(f"Keycloak sync complete — {len(users)} users scanned, {synced} updated")
            return 0
        except Exception as exc:  # pragma: no cover - runtime bootstrap
            print(f"Keycloak sync retry: {exc}", file=sys.stderr)
            time.sleep(5)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
