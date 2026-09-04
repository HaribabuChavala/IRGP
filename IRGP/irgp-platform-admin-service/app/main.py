from __future__ import annotations

from fastapi import Depends, FastAPI

from app.security import require_platform_admin

app = FastAPI(title="Platform Admin Service", version="1.0.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "platform-admin-service"}


@app.get("/api/v1/admin/dashboard")
async def dashboard(_: dict = Depends(require_platform_admin)) -> dict[str, object]:
    return {
        "stats": {
            "organizations": 5,
            "active_users": 120,
            "jobs_running": 2,
        },
        "activeJobs": ["job-1", "job-2"],
    }


@app.get("/api/v1/admin/platform/stats")
async def platform_stats(_: dict = Depends(require_platform_admin)) -> dict[str, object]:
    return {
        "stats": {
            "services": 12,
            "uptime": "99.9%",
            "error_rate": "0.2%",
        }
    }
