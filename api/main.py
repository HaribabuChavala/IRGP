from contextlib import asynccontextmanager
import json

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import store
from database import init_db
from deps import (
    AUDIT_LOG_KEY,
    KEYCLOAK_ISSUER,
    VAULT_SECRET_PATH,
    SecurityContext,
    check_policy,
    get_current_user,
    get_vault_secret,
    log_denied_access,
    redis_client,
)
from routes import router as app_router

REPORTS = {
    "123": {
        "report_id": "123",
        "title": "Q4 Revenue Report",
        "tenant_id": "tenant-acme",
        "region": "us-east",
        "content": "Revenue increased by 15%...",
    },
    "456": {
        "report_id": "456",
        "title": "Q4 Revenue Report - EU",
        "tenant_id": "tenant-other",
        "region": "eu-west",
        "content": "EU revenue data...",
    },
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.seed_store(redis_client)
    init_db()
    yield


app = FastAPI(title="Instant Report Generation Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://app.localhost",
        "http://report.localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(app_router)


class ResourceInfo(BaseModel):
    type: str
    id: str
    tenant_id: str
    region: str


class PolicyCheckRequest(BaseModel):
    resource: ResourceInfo
    action: str


class ReportResponse(BaseModel):
    report_id: str
    title: str
    tenant_id: str
    region: str
    content: str


@app.get("/health")
async def health():
    return {"status": "UP", "service": "report-api"}


@app.get("/api/v1/security/test")
async def security_test():
    return {"message": "Request reached FastAPI through Traefik", "next_step": "JWT authentication"}


@app.get("/api/v1/security/me")
async def security_me(user: SecurityContext = Depends(get_current_user)):
    return {"authenticated": True, **user.to_dict(), "issuer": KEYCLOAK_ISSUER}


@app.get("/api/v1/security/secrets-test")
async def secrets_test(user: SecurityContext = Depends(get_current_user)):
    try:
        secrets = await get_vault_secret()
        return {
            "vault_connected": True,
            "secret_path": VAULT_SECRET_PATH,
            "secrets_found": len(secrets) > 0,
            "secrets": secrets,
            "requested_by": user.username,
        }
    except Exception as exc:
        return JSONResponse(status_code=502, content={"vault_connected": False, "error": str(exc)})


@app.post("/api/v1/policy/check")
async def policy_check(request: PolicyCheckRequest, user: SecurityContext = Depends(get_current_user)):
    from deps import OPA_URL
    import httpx

    opa_input = {"input": {"user": user.to_dict(), "resource": request.resource.model_dump(), "action": request.action}}
    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.post(f"{OPA_URL}/v1/data/report/authz/allow", json=opa_input)
    if response.status_code != 200:
        return JSONResponse(status_code=502, content={"error": "OPA unavailable", "details": response.text})
    result = response.json().get("result", False)
    if not result:
        raise HTTPException(status_code=403, detail="Access denied by policy")
    return {
        "allowed": True,
        "policy_engine": "OPA",
        "user": user.username,
        "resource": request.resource.model_dump(),
        "action": request.action,
    }


@app.get("/api/v1/reports/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str, user: SecurityContext = Depends(get_current_user)):
    report = REPORTS.get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    resource = {"type": "report", "id": report_id, "tenant_id": report["tenant_id"], "region": report["region"]}
    allowed = await check_policy(user=user, resource=resource, action="read")
    if not allowed:
        log_denied_access(user=user, resource=resource, action="read")
        raise HTTPException(status_code=403, detail="Access denied")
    return ReportResponse(**report)


@app.delete("/api/v1/reports/{report_id}")
async def delete_report(report_id: str, user: SecurityContext = Depends(get_current_user)):
    report = REPORTS.get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    resource = {"type": "report", "id": report_id, "tenant_id": report["tenant_id"], "region": report["region"]}
    allowed = await check_policy(user=user, resource=resource, action="admin")
    if not allowed:
        log_denied_access(user=user, resource=resource, action="admin")
        raise HTTPException(status_code=403, detail="Access denied")
    del REPORTS[report_id]
    return {"deleted": True, "report_id": report_id, "deleted_by": user.username}


@app.get("/api/v1/audit/denied")
async def get_denied_audit_log(user: SecurityContext = Depends(get_current_user)):
    if "REPORT_ADMIN" not in user.roles and "PLATFORM_ADMIN" not in user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    entries = redis_client.lrange(AUDIT_LOG_KEY, 0, -1)
    return {"total": len(entries), "entries": [json.loads(e) for e in entries]}
