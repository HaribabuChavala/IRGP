import importlib
import os
import tempfile

import vault_client


def test_default_roles_are_seeded_into_db():
    db_path = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"

    import database
    import models

    importlib.reload(database)
    importlib.reload(models)

    database.init_db()
    with database.SessionLocal() as db:
        role_names = {row.name for row in db.query(models.Role).all()}

    database.engine.dispose()
    os.remove(db_path)
    assert {"PLATFORM_ADMIN", "REPORT_ADMIN", "REPORT_USER"}.issubset(role_names)


def test_legacy_organizations_schema_is_reset_on_init():
    db_path = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"

    import database

    importlib.reload(database)

    with database.engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE organizations (organization_id TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'inactive')")
        conn.exec_driver_sql("CREATE TABLE roles (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE)")
        conn.exec_driver_sql("CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, username TEXT NOT NULL)")
        conn.exec_driver_sql("CREATE TABLE user_roles (user_id TEXT NOT NULL, role_id INTEGER NOT NULL)")

    database.init_db()

    inspector = database.inspect(database.engine)
    columns = {column["name"] for column in inspector.get_columns("organizations")}

    database.engine.dispose()
    os.remove(db_path)
    assert {"id", "name"}.issubset(columns)


def test_security_context_resolves_tenant_from_keycloak_subject_when_claim_missing():
    db_path = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"

    import database
    import deps
    import models

    importlib.reload(database)
    importlib.reload(models)
    importlib.reload(deps)

    database.init_db()
    with database.SessionLocal() as db:
        org = models.Organization(
            id="org-123",
            name="Acme Financial",
            plan="starter",
            status="active",
            region="us-east",
            contact_email="ops@acme.com",
        )
        db.add(org)
        db.add(
            models.User(
                id="user-123",
                keycloak_user_id="kc-sub-123",
                email="tenant-lookup@acme.com",
                username="tenant-lookup",
                full_name="Org Admin",
                organization_id="org-123",
                tenant_id="org-123",
                region="us-east",
                organization_name="Acme Financial",
            )
        )
        db.commit()

    context = deps.SecurityContext({
        "sub": "kc-sub-123",
        "preferred_username": "different-user",
        "email": "missing-claim@example.com",
        "realm_access": {"roles": ["REPORT_ADMIN"]},
    })

    database.engine.dispose()
    os.remove(db_path)
    assert context.tenant_id == "org-123"


def test_vault_path_normalizer_handles_kv2_paths():
    mount, path = vault_client._normalize_vault_path("secret/data/report-platform")
    assert mount == "secret"
    assert path == "report-platform"

    mount, path = vault_client._normalize_vault_path("secret/data/report-platform/tenant-1/datasources/source-1")
    assert mount == "secret"
    assert path == "report-platform/tenant-1/datasources/source-1"


def test_report_jobs_sync_redis_data_sources_into_db_before_insert():
    db_path = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"

    import database
    import models
    import routes

    importlib.reload(database)
    importlib.reload(models)
    importlib.reload(routes)

    database.init_db()
    source = {
        "id": "ds-oracle-1",
        "name": "Local Oracle Lab",
        "type": "oracle",
        "host": "oracle",
        "port": 1521,
        "database": "FREEPDB1",
        "schema": "report_owner",
        "filePath": None,
        "accessMode": "read",
        "status": "connected",
        "lastValidatedAt": "2026-08-29T00:00:00Z",
        "queryCount": 0,
    }

    routes._ensure_data_source_exists(source, "org-acme")

    with database.SessionLocal() as db:
        row = db.query(models.DataSource).filter(models.DataSource.id == "ds-oracle-1").one()
        assert row.organization_id == "org-acme"
        assert row.name == "Local Oracle Lab"

    database.engine.dispose()
    os.remove(db_path)
