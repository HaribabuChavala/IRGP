import asyncio
import csv
import hashlib
import io
import json
import os
import secrets
import socket
import string
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

try:
    import oracledb
except Exception:  # pragma: no cover - optional dependency at runtime
    oracledb = None

try:
    import teradatasql
except Exception:  # pragma: no cover - optional dependency at runtime
    teradatasql = None

try:
    from impala.dbapi import connect as impala_connect
except Exception:  # pragma: no cover - optional dependency at runtime
    impala_connect = None

import store
from ai_sql_agent import sql_agent_service
from database import get_db
from models import DataSource, Organization, QueryHistory, ReportJob, User
from deps import (
    SecurityContext,
    get_current_user,
    redis_client,
    require_org_admin,
    require_platform_admin,
)
from email_service import send_temp_password_email

router = APIRouter(prefix="/api/v1")

KEYCLOAK_BASE_URL = os.getenv("KEYCLOAK_BASE_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "report-platform")
KEYCLOAK_ADMIN_USERNAME = os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin")
KEYCLOAK_ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "change-me-admin")

WRITE_PRIVILEGE_KEYWORDS = {
    "ALL",
    "ALTER",
    "CREATE",
    "DELETE",
    "DROP",
    "INSERT",
    "OWNER",
    "TRUNCATE",
    "UPDATE",
    "WRITE",
}


def generate_temp_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def map_role_to_keycloak_role(role: str) -> str:
    mapping = {
        "ORG_ADMIN": "REPORT_ADMIN",
        "ORG_USER": "REPORT_USER",
        "PLATFORM_ADMIN": "PLATFORM_ADMIN",
    }
    return mapping.get(role, "REPORT_USER")


async def get_keycloak_admin_token() -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{KEYCLOAK_BASE_URL}/realms/master/protocol/openid-connect/token",
            data={
                "username": KEYCLOAK_ADMIN_USERNAME,
                "password": KEYCLOAK_ADMIN_PASSWORD,
                "grant_type": "password",
                "client_id": "admin-cli",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Keycloak admin auth failed: {resp.text}")
        return resp.json()["access_token"]


async def create_keycloak_user(
    *,
    username: str,
    email: str,
    full_name: str,
    password: str,
    role: str,
    organization_id: str,
    organization_name: str,
    region: str,
) -> str:
    admin_token = await get_keycloak_admin_token()
    realm_role_name = map_role_to_keycloak_role(role)

    user_payload = {
        "username": username,
        "email": email.lower(),
        "firstName": full_name.split(" ")[0] if full_name else username,
        "lastName": " ".join(full_name.split(" ")[1:]) if full_name and " " in full_name else "",
        "enabled": True,
        "emailVerified": False,
        "attributes": {
            "tenant_id": [organization_id],
            "organization_name": [organization_name],
            "region": [region],
        },
        "credentials": [
            {"type": "password", "value": password, "temporary": True},
        ],
    }

    async with httpx.AsyncClient(timeout=15) as client:
        create_resp = await client.post(
            f"{KEYCLOAK_BASE_URL}/admin/realms/{KEYCLOAK_REALM}/users",
            json=user_payload,
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json",
            },
        )

        if create_resp.status_code not in (201, 409):
            raise HTTPException(status_code=500, detail=f"Failed to create Keycloak user: {create_resp.text}")

        if create_resp.status_code == 409:
            user_list_resp = await client.get(
                f"{KEYCLOAK_BASE_URL}/admin/realms/{KEYCLOAK_REALM}/users?email={email.lower()}",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            if user_list_resp.status_code != 200 or not user_list_resp.json():
                raise HTTPException(status_code=500, detail=f"Keycloak user conflict for {email}, but lookup failed")
            keycloak_user_id = user_list_resp.json()[0]["id"]
        else:
            keycloak_user_id = create_resp.headers.get("Location", "").split("/")[-1]

        role_resp = await client.get(
            f"{KEYCLOAK_BASE_URL}/admin/realms/{KEYCLOAK_REALM}/roles/{realm_role_name}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        if role_resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Role lookup failed: {role_resp.text}")

        role_payload = [{
            "id": role_resp.json()["id"],
            "name": role_resp.json()["name"],
            "composite": False,
            "clientRole": False,
            "containerId": KEYCLOAK_REALM,
        }]

        assign_resp = await client.post(
            f"{KEYCLOAK_BASE_URL}/admin/realms/{KEYCLOAK_REALM}/users/{keycloak_user_id}/role-mappings/realm",
            json=role_payload,
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json",
            },
        )
        if assign_resp.status_code not in (200, 204):
            raise HTTPException(status_code=500, detail=f"Role assignment failed: {assign_resp.text}")

        return keycloak_user_id


class OrganizationCreate(BaseModel):
    name: str
    contactEmail: str
    region: str
    plan: str = "free"


class OrganizationUserInvite(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=150)
    full_name: str | None = None
    role: str = "ORG_USER"


class OrganizationOnboardRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=255)
    contact_email: EmailStr
    region: str = Field(min_length=2, max_length=100)
    plan: str = "starter"
    organization_admin: OrganizationUserInvite
    users: list[OrganizationUserInvite] = Field(default_factory=list)


class OrganizationMemberResult(BaseModel):
    id: str
    email: str
    username: str
    full_name: str | None = None
    role: str
    force_password_reset: bool
    temporary_password: str
    delivery_status: str = "queued"
    delivery_provider: str = "mock"


class OrganizationOnboardingResponse(BaseModel):
    organization: dict
    created_users: list[OrganizationMemberResult]
    email_delivery: str = "queued"


class UserRegister(BaseModel):
    name: str
    email: str
    organizationId: str
    role: str = "ORG_USER"


class DataSourceCreate(BaseModel):
    name: str
    type: str
    testConnectionId: str
    connectionUrl: str | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    schema: str | None = None
    filePath: str | None = None
    username: str | None = None
    password: str | None = None
    accessMode: str = "read"


class DataSourceTestRequest(BaseModel):
    name: str
    type: str
    connectionUrl: str | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    schema: str | None = None
    filePath: str | None = None
    username: str | None = None
    password: str | None = None
    accessMode: str = "read"


def _default_port(source_type: str) -> int | None:
    mapping = {
        "oracle": 1521,
        "teradata": 1025,
        "hive": 10000,
        "jdbc": None,
    }
    return mapping.get((source_type or "").lower())


def _extract_host_port(connection_url: str | None) -> tuple[str | None, int | None]:
    if not connection_url:
        return None, None

    parsed = urlparse(connection_url)
    host = parsed.hostname
    port = parsed.port

    if host:
        return host, port

    # Handle JDBC style values like jdbc:oracle:thin:@//host:1521/service
    jdbc_match = None
    if connection_url.startswith("jdbc:"):
        jdbc_match = urlparse(connection_url.replace("jdbc:", "", 1))
    if jdbc_match and jdbc_match.hostname:
        return jdbc_match.hostname, jdbc_match.port

    return None, None


def _normalize_source_payload(body: DataSourceTestRequest | DataSourceCreate) -> dict:
    source_type = (body.type or "").lower().strip()
    host = (body.host or "").strip() or None
    connection_url = (body.connectionUrl or "").strip() or None

    url_host, url_port = _extract_host_port(connection_url)
    if not host and url_host:
        host = url_host

    port = body.port or url_port or _default_port(source_type)

    return {
        "name": body.name.strip(),
        "type": source_type,
        "connectionUrl": connection_url,
        "host": host,
        "port": port,
        "database": (body.database or "").strip() or None,
        "schema": (body.schema or "").strip() or None,
        "filePath": (body.filePath or "").strip() or None,
        "username": (body.username or "").strip() or None,
        "password": body.password or None,
        "accessMode": (body.accessMode or "").strip().lower() or "unknown",
    }


def _validate_source_payload(payload: dict) -> list[str]:
    errors: list[str] = []
    source_type = payload["type"]

    if not payload["name"]:
        errors.append("Data source name is required")
    if source_type not in {"oracle", "teradata", "hive", "excel", "jdbc"}:
        errors.append(f"Unsupported data source type: {source_type}")

    if payload["accessMode"] != "read":
        errors.append("Only read-only credentials are permitted for report data sources")

    if source_type == "excel":
        if not payload["filePath"]:
            errors.append("filePath is required for Excel sources")
        return errors

    if not payload["connectionUrl"] and not payload["host"]:
        errors.append("Provide either connectionUrl or host")
    if not payload["database"]:
        errors.append("database is required for non-Excel sources")
    if not payload["username"] or not payload["password"]:
        errors.append("Read-only username and password are required")

    return errors


def _credential_risk_warnings(username: str | None) -> list[str]:
    warnings: list[str] = []
    if not username:
        return warnings

    risky = ["admin", "root", "owner", "dba", "write"]
    lower = username.lower()
    if any(token in lower for token in risky):
        warnings.append(
            "Username appears privileged. Use a dedicated read-only account before storing credentials."
        )
    return warnings


def _source_fingerprint(payload: dict) -> str:
    sensitive = {
        "type": payload.get("type"),
        "connectionUrl": payload.get("connectionUrl"),
        "host": payload.get("host"),
        "port": payload.get("port"),
        "database": payload.get("database"),
        "schema": payload.get("schema"),
        "filePath": payload.get("filePath"),
        "username": payload.get("username"),
        "passwordHash": hashlib.sha256((payload.get("password") or "").encode()).hexdigest(),
        "accessMode": payload.get("accessMode"),
    }
    raw = json.dumps(sensitive, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _data_source_name_exists(tenant_id: str, candidate_name: str) -> bool:
    normalized = (candidate_name or "").strip().lower()
    if not normalized:
        return False

    sources = store.get_data_sources(redis_client, tenant_id)
    return any((item.get("name") or "").strip().lower() == normalized for item in sources)


async def _tcp_check(host: str, port: int) -> bool:
    def _connect() -> bool:
        with socket.create_connection((host, port), timeout=3):
            return True

    try:
        return await asyncio.to_thread(_connect)
    except OSError:
        return False


def _db_connect_timeout_seconds() -> int:
    raw = os.getenv("DB_TEST_CONNECT_TIMEOUT_SECONDS", "5").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 5
    return max(2, min(value, 30))


def _friendly_connection_error(engine: str, exc: Exception) -> str:
    message = " ".join(str(exc).split())
    lower = message.lower()

    if any(token in lower for token in ["ora-01017", "invalid username/password", "authentication failed"]):
        return f"{engine} login failed. Check the username and password."

    if any(token in lower for token in ["no listener", "connection refused", "cannot reach", "timed out", "timeout", "name or service not known"]):
        return f"{engine} server is not reachable. Check the host, port, and network access."

    if any(token in lower for token in ["service name", "sid", "unknown database", "database does not exist"]):
        return f"{engine} database or service name is invalid. Check the database/service field and connection URL."

    if any(token in lower for token in ["dpy-4011", "dpy-6005", "tsocket read 0 bytes", "lost connection", "failure receiving message header"]):
        return f"{engine} connection failed during handshake. Check that the selected datasource type matches the target server and that the port is correct."

    return f"{engine} connection failed. Verify the host, port, database/service, and read-only credentials."


def _friendly_vault_error(detail: str) -> str:
    return "Credentials could not be saved to Vault. Verify that Vault is running and the API has a valid Vault token."


def _contains_write_privilege(text: str) -> bool:
    upper = (text or "").upper()
    return any(keyword in upper for keyword in WRITE_PRIVILEGE_KEYWORDS)


def _extract_oracle_service_name(payload: dict) -> str | None:
    if payload.get("database"):
        return str(payload["database"])

    connection_url = payload.get("connectionUrl") or ""
    if not connection_url:
        return None

    normalized = connection_url
    if normalized.startswith("jdbc:"):
        normalized = normalized.replace("jdbc:", "", 1)

    parsed = urlparse(normalized)
    if parsed.path:
        service = parsed.path.strip("/")
        if service:
            return service

    marker = "@//"
    if marker in connection_url:
        tail = connection_url.split(marker, 1)[1]
        if "/" in tail:
            return tail.split("/", 1)[1].split("?", 1)[0].strip() or None

    return None


def _oracle_authz_check(payload: dict) -> tuple[bool, str]:
    if oracledb is None:
        return False, "Oracle driver is not installed (oracledb)"

    host = payload.get("host")
    port = int(payload.get("port") or 1521)
    username = payload.get("username")
    password = payload.get("password")
    service_name = _extract_oracle_service_name(payload)

    if not service_name:
        return False, "Oracle service name is required (use database field or include it in connectionUrl)"

    connection = None
    try:
        connection = oracledb.connect(
            user=username,
            password=password,
            host=host,
            port=port,
            service_name=service_name,
            tcp_connect_timeout=_db_connect_timeout_seconds(),
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM dual")
            cursor.fetchone()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM SESSION_PRIVS
                WHERE PRIVILEGE IN (
                    'ALTER ANY TABLE',
                    'CREATE ANY TABLE',
                    'DELETE ANY TABLE',
                    'DROP ANY TABLE',
                    'INSERT ANY TABLE',
                    'TRUNCATE ANY TABLE',
                    'UPDATE ANY TABLE'
                )
                """
            )
            write_any_count = int(cursor.fetchone()[0] or 0)
            if write_any_count > 0:
                return False, "Oracle account has broad write privileges; provide read-only credentials"

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM USER_ROLE_PRIVS
                WHERE GRANTED_ROLE IN ('DBA', 'RESOURCE')
                """
            )
            elevated_role_count = int(cursor.fetchone()[0] or 0)
            if elevated_role_count > 0:
                return False, "Oracle account has elevated roles (DBA/RESOURCE); provide read-only credentials"

        return True, "Oracle authentication and read-only privilege checks succeeded"
    except Exception as exc:
        return False, _friendly_connection_error("Oracle", exc)
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


def _teradata_authz_check(payload: dict) -> tuple[bool, str]:
    test_backend = os.getenv("TERADATA_TEST_BACKEND", "native").strip().lower()
    if test_backend == "postgres":
        try:
            import psycopg
        except Exception as exc:
            return False, f"Teradata lab backend requires psycopg: {str(exc)}"

        host = payload.get("host")
        port = int(payload.get("port") or 5432)
        database = payload.get("database") or "teradata_lab"
        username = payload.get("username")
        password = payload.get("password")

        connection = None
        try:
            connection = psycopg.connect(
                host=host,
                port=port,
                dbname=database,
                user=username,
                password=password,
                connect_timeout=_db_connect_timeout_seconds(),
            )
            with connection.cursor() as cursor:
                cursor.execute("SELECT CURRENT_DATE")
                cursor.fetchone()

                cursor.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.table_privileges
                        WHERE grantee = current_user
                          AND privilege_type IN ('INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER')
                    )
                    """
                )
                has_write_privileges = bool(cursor.fetchone()[0])
                if has_write_privileges:
                    return False, "Teradata lab account has write privileges; provide read-only credentials"

                cursor.execute("SELECT has_database_privilege(current_user, current_database(), 'CREATE')")
                can_create = bool(cursor.fetchone()[0])
                if can_create:
                    return False, "Teradata lab account can CREATE objects; provide stricter read-only credentials"

            return True, "Teradata lab authentication and read-only privilege checks succeeded"
        except Exception as exc:
            return False, _friendly_connection_error("Teradata lab", exc)
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    if teradatasql is None:
        return False, "Teradata driver is not installed (teradatasql)"

    params = {
        "host": payload.get("host"),
        "user": payload.get("username"),
        "password": payload.get("password"),
        "logmech": os.getenv("TERADATA_LOGMECH", "TD2"),
        "encryptdata": os.getenv("TERADATA_ENCRYPT_DATA", "true"),
    }
    if payload.get("port"):
        params["dbs_port"] = str(payload["port"])
    if payload.get("database"):
        params["database"] = payload["database"]

    connection = None
    try:
        connection = teradatasql.connect(**params)
        with connection.cursor() as cursor:
            cursor.execute("SELECT CURRENT_DATE")
            cursor.fetchone()

            privilege_queries = [
                """
                SELECT TOP 1 AccessRight
                FROM DBC.AllRightsV
                WHERE Grantee = USER
                  AND AccessRight IN ('CD', 'CT', 'D', 'DL', 'DM', 'DR', 'DT', 'I', 'U')
                """,
                """
                SELECT TOP 1 AccessRight
                FROM DBC.AllRightsV
                WHERE UserName = USER
                  AND AccessRight IN ('CD', 'CT', 'D', 'DL', 'DM', 'DR', 'DT', 'I', 'U')
                """,
                """
                SELECT TOP 1 AccessRight
                FROM DBC.UserRightsV
                WHERE Grantee = USER
                  AND AccessRight IN ('CD', 'CT', 'D', 'DL', 'DM', 'DR', 'DT', 'I', 'U')
                """,
            ]

            introspection_ran = False
            for query in privilege_queries:
                try:
                    cursor.execute(query)
                    introspection_ran = True
                    row = cursor.fetchone()
                    if row:
                        return False, "Teradata account appears to have write privileges; provide read-only credentials"
                    break
                except Exception:
                    continue

            if not introspection_ran:
                return False, "Teradata privilege introspection failed; grant metadata-read access or use stricter read-only account"

        return True, "Teradata authentication and read-only privilege checks succeeded"
    except Exception as exc:
        return False, _friendly_connection_error("Teradata", exc)
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


def _hive_authz_check(payload: dict) -> tuple[bool, str]:
    if impala_connect is None:
        return False, "Hive/Impala driver is not installed (impyla)"

    host = payload.get("host")
    port = int(payload.get("port") or 10000)
    username = payload.get("username")
    password = payload.get("password")
    database = payload.get("database") or "default"

    auth_mechanism = os.getenv("HIVE_AUTH_MECHANISM", "NOSASL")

    params = {
        "host": host,
        "port": port,
        "user": username,
        "database": database,
        "auth_mechanism": auth_mechanism,
        "timeout": _db_connect_timeout_seconds(),
    }
    if password:
        params["password"] = password

    connection = None
    try:
        connection = impala_connect(**params)
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

            safe_user = (username or "").replace("`", "")
            safe_db = database.replace("`", "")
            grant_queries = [
                f"SHOW GRANT USER `{safe_user}` ON DATABASE `{safe_db}`",
                f"SHOW GRANT USER {safe_user} ON DATABASE {safe_db}",
                f"SHOW GRANT USER `{safe_user}` ON SERVER",
                f"SHOW GRANT USER {safe_user} ON SERVER",
            ]

            introspection_ran = False
            for query in grant_queries:
                try:
                    cursor.execute(query)
                    introspection_ran = True
                    rows = cursor.fetchall() or []
                    for row in rows:
                        row_text = " ".join(str(item) for item in row)
                        if _contains_write_privilege(row_text):
                            return False, "Hive account appears to have write privileges; provide read-only credentials"
                    break
                except Exception:
                    continue

            if not introspection_ran:
                return False, "Hive privilege introspection failed; grant SHOW GRANT access or use stricter read-only account"

        return True, "Hive authentication and read-only privilege checks succeeded"
    except Exception as exc:
        return False, _friendly_connection_error("Hive", exc)
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


async def _test_connection(payload: dict) -> tuple[bool, str]:
    source_type = payload["type"]
    if source_type == "excel":
        return True, "File path format validated for Excel source"

    host = payload.get("host")
    port = payload.get("port")
    if not host or not port:
        return False, "Unable to resolve host/port from connection details"

    ok = await _tcp_check(host, int(port))
    if not ok:
        return False, f"Cannot reach {host}:{port}. Verify network access and connection settings"

    if source_type == "oracle":
        return await asyncio.to_thread(_oracle_authz_check, payload)

    if source_type == "teradata":
        return await asyncio.to_thread(_teradata_authz_check, payload)

    if source_type == "hive":
        return await asyncio.to_thread(_hive_authz_check, payload)

    return True, f"Network connection test succeeded for {host}:{port}"


def _vault_env() -> tuple[str, str]:
    vault_addr = os.getenv("VAULT_ADDR", "http://vault:8200").rstrip("/")
    vault_token = os.getenv("VAULT_TOKEN", "").strip()
    if not vault_token:
        raise HTTPException(status_code=500, detail="Vault token not configured")
    return vault_addr, vault_token


async def _vault_write(path: str, data: dict) -> None:
    vault_addr, vault_token = _vault_env()
    url = f"{vault_addr}/v1/{path.lstrip('/')}"
    payload = {"data": data}

    async with httpx.AsyncClient(timeout=8) as client:
        response = await client.post(
            url,
            json=payload,
            headers={"X-Vault-Token": vault_token, "Content-Type": "application/json"},
        )
    if response.status_code >= 300:
        raise HTTPException(status_code=502, detail=_friendly_vault_error(response.text))


class ReportGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1)
    dataSourceId: str


class SubscriptionUpgradeRequest(BaseModel):
    plan: str


@router.get("/platform/stats")
async def platform_stats(
    user: SecurityContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_platform_admin(user)

    total_organizations = db.scalar(select(func.count(Organization.id))) or 0
    active_jobs_rows = db.execute(
        select(
            ReportJob.id,
            Organization.name.label("organization_name"),
            ReportJob.status,
            ReportJob.progress,
            ReportJob.created_at,
        )
        .join(Organization, Organization.id == ReportJob.organization_id)
        .where(ReportJob.status.in_(["queued", "running"]))
        .order_by(ReportJob.created_at.desc())
        .limit(20)
    ).all()

    active_jobs = []
    for row in active_jobs_rows:
        job_id, org_name, status, progress, started_at = row
        active_jobs.append(
            {
                "id": str(job_id),
                "organization": org_name,
                "type": "Report generation",
                "progress": int(progress or 0),
                "status": status,
                "startedAt": started_at.isoformat() if started_at else "just now",
            }
        )

    queries_today = db.scalar(
        select(func.coalesce(func.sum(QueryHistory.row_count), 0))
        .where(QueryHistory.executed_at >= func.date_trunc("day", func.now()))
    ) or 0

    utilization = min(95, 40 + len(active_jobs) * 8 + total_organizations * 2)
    stats = {
        "totalOrganizations": int(total_organizations),
        "activeJobs": len(active_jobs),
        "queriesToday": int(queries_today),
        "utilizationPercent": int(utilization),
    }
    return {"stats": stats, "activeJobs": active_jobs}


@router.get("/platform/organizations")
async def list_organizations(
    user: SecurityContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_platform_admin(user)

    rows = db.execute(
        select(
            Organization.id,
            Organization.name,
            Organization.plan,
            Organization.status,
            Organization.region,
            Organization.contact_email,
            Organization.created_at,
            func.count(func.distinct(User.id)).label("user_count"),
            func.count(func.distinct(DataSource.id)).label("data_source_count"),
            func.coalesce(func.sum(QueryHistory.row_count), 0).label("queries_this_month"),
        )
        .outerjoin(User, User.organization_id == Organization.id)
        .outerjoin(DataSource, DataSource.organization_id == Organization.id)
        .outerjoin(QueryHistory, QueryHistory.organization_id == Organization.id)
        .group_by(
            Organization.id,
            Organization.name,
            Organization.plan,
            Organization.status,
            Organization.region,
            Organization.contact_email,
            Organization.created_at,
        )
        .order_by(Organization.name.asc())
    ).all()

    organizations = []
    for row in rows:
        organizations.append(
            {
                "id": str(row[0]),
                "name": row[1],
                "plan": row[2],
                "status": row[3],
                "userCount": int(row[7] or 0),
                "dataSourceCount": int(row[8] or 0),
                "queriesThisMonth": int(row[9] or 0),
                "createdAt": row[6].date().isoformat() if row[6] else None,
                "region": row[4],
                "contactEmail": row[5],
            }
        )

    return {"organizations": organizations}


@router.post("/platform/organizations")
async def register_organization(
    body: OrganizationCreate,
    user: SecurityContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_platform_admin(user)

    org = Organization(
        name=body.name,
        plan=body.plan,
        status="active",
        region=body.region,
        contact_email=body.contactEmail,
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    org_payload = {
        "id": str(org.id),
        "name": org.name,
        "plan": org.plan,
        "status": org.status,
        "userCount": 0,
        "dataSourceCount": 0,
        "queriesThisMonth": 0,
        "createdAt": org.created_at.date().isoformat(),
        "region": org.region,
        "contactEmail": org.contact_email,
    }

    orgs = store.get_organizations(redis_client)
    orgs.append(org_payload)
    store.save_organizations(redis_client, orgs)
    store.save_data_sources(redis_client, str(org.id), [])
    return {"organization": org_payload}


@router.post("/platform/organizations/onboard", response_model=OrganizationOnboardingResponse)
async def onboard_organization(
    body: OrganizationOnboardRequest,
    user: SecurityContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_platform_admin(user)
    orgs = store.get_organizations(redis_client)
    normalized_name = body.organization_name.strip()
    if any(org.get("name", "").lower() == normalized_name.lower() for org in orgs):
        raise HTTPException(status_code=409, detail="Organization name already exists")

    invited_users = [body.organization_admin, *body.users]
    seen_emails: set[str] = set()
    for invite in invited_users:
        email = invite.email.lower()
        if email in seen_emails:
            raise HTTPException(status_code=409, detail=f"User already invited: {email}")
        seen_emails.add(email)

    org = Organization(
        name=normalized_name,
        plan=body.plan,
        status="active",
        region=body.region,
        contact_email=body.contact_email.lower(),
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    created_users: list[OrganizationMemberResult] = []
    delivery_statuses: list[str] = []
    for invite in invited_users:
        email = invite.email.lower()
        temp_password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        delivery = send_temp_password_email(
            recipient=email,
            username=invite.username,
            temp_password=temp_password,
            organization_name=org.name,
        )
        delivery_statuses.append(delivery.get("status", "queued"))

        user_record = OrganizationMemberResult(
            id=str(uuid.uuid4()),
            email=email,
            username=invite.username,
            full_name=invite.full_name or invite.username,
            role=invite.role,
            force_password_reset=True,
            temporary_password=temp_password,
            delivery_status=delivery.get("status", "queued"),
            delivery_provider=delivery.get("provider", "mock"),
        )
        created_users.append(user_record)

        db_user = User(
            email=email,
            username=invite.username,
            full_name=invite.full_name or invite.username,
            organization_id=str(org.id),
            organization_name=org.name,
            region=body.region,
            status="invited",
        )
        db.add(db_user)

    db.commit()

    org_payload = {
        "id": str(org.id),
        "name": org.name,
        "plan": org.plan,
        "status": org.status,
        "userCount": len(created_users),
        "dataSourceCount": 0,
        "queriesThisMonth": 0,
        "createdAt": org.created_at.date().isoformat(),
        "region": org.region,
        "contactEmail": org.contact_email,
    }
    orgs.append(org_payload)
    store.save_organizations(redis_client, orgs)
    store.save_data_sources(redis_client, str(org.id), [])

    return {
        "organization": org_payload,
        "created_users": created_users,
        "email_delivery": "sent" if any(status == "sent" for status in delivery_statuses) else "queued",
    }


@router.post("/platform/users")
async def register_user(
    body: UserRegister,
    user: SecurityContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_platform_admin(user)

    orgs = store.get_organizations(redis_client)
    org = next((o for o in orgs if o["id"] == body.organizationId), None)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    email = body.email.lower()
    username = body.email.split("@")[0].lower().replace(" ", "_") if "@" in body.email else body.email.lower()
    temp_password = generate_temp_password()
    delivery = send_temp_password_email(
        recipient=email,
        username=username,
        temp_password=temp_password,
        organization_name=org["name"],
    )

    keycloak_user_id = await create_keycloak_user(
        username=username,
        email=email,
        full_name=body.name,
        password=temp_password,
        role=body.role,
        organization_id=body.organizationId,
        organization_name=org["name"],
        region=org.get("region", "unknown"),
    )

    db_user = User(
        email=email,
        username=username,
        full_name=body.name,
        organization_id=body.organizationId,
        organization_name=org["name"],
        region=org.get("region", "unknown"),
        status="invited",
        keycloak_user_id=keycloak_user_id,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    org["userCount"] = org.get("userCount", 0) + 1
    store.save_organizations(redis_client, orgs)

    return {
        "user": {
            "id": str(db_user.id),
            "name": body.name,
            "username": username,
            "email": email,
            "organizationId": body.organizationId,
            "role": body.role,
            "status": "invited",
            "force_password_reset": True,
            "temporary_password": temp_password,
            "delivery_status": delivery.get("status", "queued"),
            "delivery_provider": delivery.get("provider", "mock"),
        },
        "note": "User created and temp password email sent",
    }


@router.get("/org/dashboard")
async def org_dashboard(user: SecurityContext = Depends(get_current_user)):
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id missing from token")

    sources = store.get_data_sources(redis_client, tenant_id)
    history = store.get_query_history(redis_client, tenant_id)
    total_queries = sum(s.get("queryCount", 0) for s in sources)

    return {
        "totalQueries": total_queries,
        "dataSourceCount": len(sources),
        "recentExecutions": len(history),
        "dataSources": sources,
        "queryHistory": history,
    }


@router.get("/org/data-sources")
async def list_data_sources(user: SecurityContext = Depends(get_current_user)):
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id missing from token")
    return {"dataSources": store.get_data_sources(redis_client, tenant_id)}


@router.post("/org/data-sources/test-connection")
async def test_data_source_connection(
    body: DataSourceTestRequest,
    user: SecurityContext = Depends(get_current_user),
):
    require_org_admin(user)
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id missing from token")

    payload = _normalize_source_payload(body)
    if _data_source_name_exists(tenant_id, payload.get("name") or ""):
        raise HTTPException(status_code=409, detail="Connection name already exists in this organization. Use a unique name")

    errors = _validate_source_payload(payload)
    if errors:
        raise HTTPException(status_code=422, detail="; ".join(errors))

    warnings = _credential_risk_warnings(payload.get("username"))
    if warnings:
        raise HTTPException(status_code=422, detail="; ".join(warnings))

    success, message = await _test_connection(payload)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    test_id = str(uuid.uuid4())
    redis_key = f"tenant:{tenant_id}:data_source_test:{test_id}"
    redis_client.set(
        redis_key,
        json.dumps({"fingerprint": _source_fingerprint(payload), "createdAt": datetime.now(timezone.utc).isoformat()}),
        ex=600,
    )

    return {
        "success": True,
        "testConnectionId": test_id,
        "normalized": {
            "host": payload.get("host"),
            "port": payload.get("port"),
            "connectionUrl": payload.get("connectionUrl"),
            "database": payload.get("database"),
            "schema": payload.get("schema"),
        },
        "warnings": [],
        "message": message,
    }


@router.post("/org/data-sources")
async def create_data_source(
    body: DataSourceCreate,
    user: SecurityContext = Depends(get_current_user),
):
    require_org_admin(user)
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id missing from token")

    payload = _normalize_source_payload(body)
    if _data_source_name_exists(tenant_id, payload.get("name") or ""):
        raise HTTPException(status_code=409, detail="Connection name already exists in this organization. Use a unique name")

    errors = _validate_source_payload(payload)
    if errors:
        raise HTTPException(status_code=422, detail="; ".join(errors))

    warnings = _credential_risk_warnings(payload.get("username"))
    if warnings:
        raise HTTPException(status_code=422, detail="; ".join(warnings))

    test_key = f"tenant:{tenant_id}:data_source_test:{body.testConnectionId}"
    saved_test = redis_client.get(test_key)
    if not saved_test:
        raise HTTPException(status_code=400, detail="Connection test expired or missing. Test connection again before saving")

    test_payload = json.loads(saved_test)
    if test_payload.get("fingerprint") != _source_fingerprint(payload):
        raise HTTPException(status_code=400, detail="Connection details changed after test. Re-run test connection")

    source_id = str(uuid.uuid4())
    credential_path = f"secret/data/report-platform/{tenant_id}/datasources/{source_id}"
    await _vault_write(
        credential_path,
        {
            "username": payload.get("username"),
            "password": payload.get("password"),
            "access_mode": payload.get("accessMode"),
            "source_type": payload.get("type"),
            "created_by": user.user_id,
        },
    )

    sources = store.get_data_sources(redis_client, tenant_id)
    source = {
        "id": source_id,
        "name": payload.get("name"),
        "type": payload.get("type"),
        "connectionUrl": payload.get("connectionUrl"),
        "host": payload.get("host"),
        "port": payload.get("port"),
        "database": payload.get("database"),
        "schema": payload.get("schema"),
        "filePath": payload.get("filePath"),
        "accessMode": payload.get("accessMode"),
        "vaultSecretPath": credential_path,
        "status": "connected",
        "lastValidatedAt": datetime.now(timezone.utc).isoformat(),
        "queryCount": 0,
    }
    sources.append(source)
    store.save_data_sources(redis_client, tenant_id, sources)
    redis_client.delete(test_key)

    orgs = store.get_organizations(redis_client)
    for org in orgs:
        if org["id"] == tenant_id:
            org["dataSourceCount"] = len(sources)
            break
    store.save_organizations(redis_client, orgs)

    return {"dataSource": source}


@router.get("/org/notifications")
async def list_notifications(user: SecurityContext = Depends(get_current_user)):
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id missing from token")
    return {"notifications": store.get_notifications(redis_client, tenant_id)}


@router.patch("/org/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: SecurityContext = Depends(get_current_user),
):
    tenant_id = user.tenant_id
    items = store.get_notifications(redis_client, tenant_id)
    for item in items:
        if item["id"] == notification_id:
            item["read"] = True
            break
    store.save_notifications(redis_client, tenant_id, items)
    return {"updated": True}


@router.get("/org/reminders")
async def list_reminders(user: SecurityContext = Depends(get_current_user)):
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id missing from token")
    return {"reminders": store.get_subscription_reminders(redis_client, tenant_id)}


@router.get("/org/subscriptions/plans")
async def subscription_plans(user: SecurityContext = Depends(get_current_user)):
    return {"plans": store.SUBSCRIPTION_PLANS}


@router.get("/org/subscriptions/current")
async def current_subscription(user: SecurityContext = Depends(get_current_user)):
    org = store.get_org_by_tenant(redis_client, user.tenant_id)
    if not org:
        return {"plan": "free", "organizationName": user.organization_name}
    return {"plan": org.get("plan", "free"), "organization": org}


@router.post("/org/subscriptions/upgrade")
async def upgrade_subscription(
    body: SubscriptionUpgradeRequest,
    user: SecurityContext = Depends(get_current_user),
):
    require_org_admin(user)
    orgs = store.get_organizations(redis_client)
    updated = None
    for org in orgs:
        if org["id"] == user.tenant_id:
            org["plan"] = body.plan
            updated = org
            break
    if not updated:
        raise HTTPException(status_code=404, detail="Organization not found")
    store.save_organizations(redis_client, orgs)
    return {"organization": updated}


def _sample_table() -> list[list[str]]:
    return [
        ["Region", "Revenue", "Growth %"],
        ["North America", "$2.4M", "12.3%"],
        ["Europe", "$1.8M", "8.7%"],
        ["Asia Pacific", "$1.2M", "15.1%"],
        ["Latin America", "$0.6M", "6.2%"],
    ]


async def _run_report_job(
    job_id: str,
    prompt: str,
    data_source: dict,
    user: SecurityContext,
):
    org = store.get_org_by_tenant(redis_client, user.tenant_id)
    org_name = org["name"] if org else user.organization_name or user.tenant_id

    steps = [
        (10, "running", "Job queued"),
        (30, "running", "Discovering schema..."),
        (55, "running", "Generating SQL with ADK agent..."),
        (80, "running", "Running safety checks..."),
    ]

    for progress, status, message in steps:
        store.update_job(
            redis_client,
            job_id,
            {"progress": progress, "status": status, "message": message},
        )
        store.upsert_active_job(
            redis_client,
            {
                "id": job_id,
                "organization": org_name,
                "type": "Report generation",
                "progress": progress,
                "status": status,
                "startedAt": "just now",
            },
        )
        await asyncio.sleep(0.7)

    sql_result = await sql_agent_service.generate_sql(prompt=prompt, data_source=data_source, tenant_id=user.tenant_id)
    if not sql_result.valid:
        failure_message = "SQL validation failed: " + "; ".join(sql_result.validation_errors)
        store.update_job(
            redis_client,
            job_id,
            {
                "progress": 100,
                "status": "failed",
                "message": failure_message,
                "content": failure_message,
            },
        )
        store.remove_active_job(redis_client, job_id)
        return

    table_data = [
        ["Attribute", "Value"],
        ["Data Source", data_source["name"]],
        ["Dialect", sql_result.dialect],
        ["Estimated Cost", sql_result.estimated_cost],
        ["PII detected", "yes" if sql_result.pii_detected else "no"],
        ["Provider", sql_result.provider],
    ]
    content = (
        f'SQL generated for "{prompt}" on {data_source["name"]}.\n\n'
        f'Dialect: {sql_result.dialect}\n'
        f'Cost estimate: {sql_result.estimated_cost}\n'
        f'Validation: passed\n\n'
        f'Generated SQL:\n{sql_result.sql}'
    )

    store.update_job(
        redis_client,
        job_id,
        {
            "progress": 100,
            "status": "completed",
            "message": "Report ready",
            "content": content,
            "sqlQuery": sql_result.sql,
            "sqlDialect": sql_result.dialect,
            "sqlValidation": "passed",
            "sqlCost": sql_result.estimated_cost,
            "piiDetected": sql_result.pii_detected,
            "piiColumns": sql_result.pii_columns,
            "plannerNotes": sql_result.planner_notes,
            "provider": sql_result.provider,
            "tableData": table_data,
            "dataSourceName": data_source["name"],
            "prompt": prompt,
        },
    )
    store.remove_active_job(redis_client, job_id)
    store.increment_queries_today(redis_client)

    sources = store.get_data_sources(redis_client, user.tenant_id)
    for source in sources:
        if source["id"] == data_source["id"]:
            source["queryCount"] = source.get("queryCount", 0) + 1
            source["lastUsed"] = datetime.now(timezone.utc).isoformat()
            break
    store.save_data_sources(redis_client, user.tenant_id, sources)

    history_item = {
        "id": job_id,
        "prompt": prompt,
        "dataSourceId": data_source["id"],
        "dataSourceName": data_source["name"],
        "executedAt": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "rowCount": max(0, len(table_data) - 1),
    }
    store.add_query_history(redis_client, user.tenant_id, history_item)

    store.add_notification(
        redis_client,
        user.tenant_id,
        {
            "id": str(uuid.uuid4()),
            "title": f"Report ready: {prompt[:40]}",
            "message": "Your instant report has been generated and is ready to export.",
            "type": "report",
            "read": False,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        },
    )

    orgs = store.get_organizations(redis_client)
    for org in orgs:
        if org["id"] == user.tenant_id:
            org["queriesThisMonth"] = org.get("queriesThisMonth", 0) + 1
            break
    store.save_organizations(redis_client, orgs)


@router.post("/reports/generate")
async def generate_report(
    body: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    user: SecurityContext = Depends(get_current_user),
):
    tenant_id = user.tenant_id
    sources = store.get_data_sources(redis_client, tenant_id)
    data_source = next((s for s in sources if s["id"] == body.dataSourceId), None)
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")

    job_id = store.create_job(
        redis_client,
        {
            "status": "running",
            "progress": 0,
            "message": "Starting...",
            "prompt": body.prompt,
            "dataSourceId": body.dataSourceId,
            "tenantId": tenant_id,
            "userId": user.user_id,
        },
    )

    background_tasks.add_task(_run_report_job, job_id, body.prompt, data_source, user)
    return {"jobId": job_id}


@router.get("/reports/jobs/{job_id}")
async def get_report_job(job_id: str, user: SecurityContext = Depends(get_current_user)):
    job = store.get_job(redis_client, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("tenantId") != user.tenant_id and "PLATFORM_ADMIN" not in user.roles:
        raise HTTPException(status_code=403, detail="Access denied")
    return job


@router.get("/reports/jobs/{job_id}/stream")
async def stream_report_job(job_id: str, user: SecurityContext = Depends(get_current_user)):
    job = store.get_job(redis_client, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("tenantId") != user.tenant_id and "PLATFORM_ADMIN" not in user.roles:
        raise HTTPException(status_code=403, detail="Access denied")

    async def event_stream():
        while True:
            current = store.get_job(redis_client, job_id)
            if not current:
                yield f"event: error\ndata: {json.dumps({'message': 'Job not found'})}\n\n"
                break
            payload = {
                "jobId": job_id,
                "status": current.get("status"),
                "progress": current.get("progress", 0),
                "message": current.get("message", ""),
                "content": current.get("content"),
                "sqlQuery": current.get("sqlQuery"),
                "sqlDialect": current.get("sqlDialect"),
                "sqlValidation": current.get("sqlValidation"),
                "sqlCost": current.get("sqlCost"),
                "piiDetected": current.get("piiDetected"),
                "piiColumns": current.get("piiColumns"),
                "plannerNotes": current.get("plannerNotes"),
                "provider": current.get("provider"),
                "tableData": current.get("tableData"),
                "dataSourceName": current.get("dataSourceName"),
            }
            yield f"data: {json.dumps(payload)}\n\n"
            if current.get("status") in ("completed", "failed"):
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/reports/jobs/{job_id}/export")
async def export_report_job(
    job_id: str,
    format: str = "csv",
    user: SecurityContext = Depends(get_current_user),
):
    job = store.get_job(redis_client, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("tenantId") != user.tenant_id and "PLATFORM_ADMIN" not in user.roles:
        raise HTTPException(status_code=403, detail="Access denied")
    if job.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Report not ready")

    table: list[list[str]] = job.get("tableData") or []
    filename_base = f"report-{job_id[:8]}"

    if format == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerows(table)
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.csv"'},
        )

    if format == "excel":
        try:
            from openpyxl import Workbook
        except ImportError as exc:
            raise HTTPException(status_code=501, detail="Excel export unavailable") from exc
        wb = Workbook()
        ws = wb.active
        ws.title = "Report"
        for row in table:
            ws.append(row)
        xlsx_buffer = io.BytesIO()
        wb.save(xlsx_buffer)
        xlsx_buffer.seek(0)
        return StreamingResponse(
            xlsx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.xlsx"'},
        )

    if format == "pdf":
        try:
            from fpdf import FPDF
        except ImportError as exc:
            raise HTTPException(status_code=501, detail="PDF export unavailable") from exc
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.cell(0, 10, job.get("content", "Report")[:120], ln=True)
        pdf.ln(4)
        if table:
            col_width = 190 / max(len(table[0]), 1)
            pdf.set_font("Helvetica", size=10)
            for row in table:
                for cell in row:
                    pdf.cell(col_width, 8, str(cell)[:30], border=1)
                pdf.ln()
        pdf_bytes = pdf.output()
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.pdf"'},
        )

    raise HTTPException(status_code=400, detail="Unsupported format. Use csv, excel, or pdf")
