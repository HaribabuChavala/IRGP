"""Redis-backed application store for the report platform lab."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

ORGANIZATIONS_KEY = "platform:organizations"
ACTIVE_JOBS_KEY = "platform:active_jobs"
QUERIES_TODAY_KEY = "platform:queries_today"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def seed_store(redis_client) -> None:
    if redis_client.get("platform:seeded"):
        return

    orgs = [
        {
            "id": "org-spartexai",
            "name": "Spartexai",
            "plan": "starter",
            "status": "active",
            "userCount": 5,
            "dataSourceCount": 2,
            "queriesThisMonth": 1840,
            "createdAt": "2026-08-24",
            "region": "us-east",
            "contactEmail": "admin@spartexai.com",
        },
        {
            "id": "org-acme",
            "name": "Acme Financial",
            "plan": "year",
            "status": "active",
            "userCount": 42,
            "dataSourceCount": 3,
            "queriesThisMonth": 12840,
            "createdAt": "2025-03-12",
            "region": "us-east",
        },
        {
            "id": "org-hsbc",
            "name": "HSBC Analytics",
            "plan": "half_year",
            "status": "active",
            "userCount": 18,
            "dataSourceCount": 3,
            "queriesThisMonth": 5620,
            "createdAt": "2025-06-01",
            "region": "uk",
        },
        {
            "id": "org-startup",
            "name": "DataStart Inc",
            "plan": "free",
            "status": "trial",
            "userCount": 4,
            "dataSourceCount": 1,
            "queriesThisMonth": 320,
            "createdAt": "2026-01-20",
            "region": "us-west",
        },
    ]
    redis_client.set(ORGANIZATIONS_KEY, json.dumps(orgs))

    acme_sources = [
        {
            "id": "ds-oracle-1",
            "name": "Production Oracle",
            "type": "oracle",
            "host": "oracle-prod.internal",
            "port": 1521,
            "database": "FINWARE",
            "status": "connected",
            "lastUsed": _now_iso(),
            "queryCount": 8420,
        },
        {
            "id": "ds-hive-1",
            "name": "Analytics Hive",
            "type": "hive",
            "host": "hive-cluster.internal",
            "port": 10000,
            "database": "analytics",
            "status": "connected",
            "lastUsed": _now_iso(),
            "queryCount": 3210,
        },
        {
            "id": "ds-excel-1",
            "name": "Monthly Sales Excel",
            "type": "excel",
            "filePath": "/data/reports/sales_2026.xlsx",
            "status": "connected",
            "lastUsed": _now_iso(),
            "queryCount": 890,
        },
    ]
    redis_client.set(_tenant_sources_key("org-acme"), json.dumps(acme_sources))

    history = [
        {
            "id": "q-001",
            "prompt": "Show Q2 revenue by region",
            "dataSourceId": "ds-oracle-1",
            "dataSourceName": "Production Oracle",
            "executedAt": _now_iso(),
            "status": "completed",
            "rowCount": 48,
        },
        {
            "id": "q-002",
            "prompt": "Top 10 customers by order volume",
            "dataSourceId": "ds-hive-1",
            "dataSourceName": "Analytics Hive",
            "executedAt": _now_iso(),
            "status": "completed",
            "rowCount": 10,
        },
    ]
    redis_client.set(_tenant_history_key("org-acme"), json.dumps(history))

    notifications = [
        {
            "id": "n-1",
            "title": "Report ready: Q2 Revenue",
            "message": "Your instant report has been generated and is ready to export.",
            "type": "report",
            "read": False,
            "createdAt": _now_iso(),
        },
        {
            "id": "n-2",
            "title": "Subscription renewal",
            "message": "Your half-year plan renews in 14 days.",
            "type": "subscription",
            "read": False,
            "createdAt": _now_iso(),
        },
    ]
    redis_client.set(_tenant_notifications_key("org-acme"), json.dumps(notifications))

    redis_client.set("platform:seeded", "1")
    redis_client.set(QUERIES_TODAY_KEY, "1842")


def _tenant_sources_key(tenant_id: str) -> str:
    return f"tenant:{tenant_id}:data_sources"


def _tenant_history_key(tenant_id: str) -> str:
    return f"tenant:{tenant_id}:query_history"


def _tenant_notifications_key(tenant_id: str) -> str:
    return f"tenant:{tenant_id}:notifications"


def _job_key(job_id: str) -> str:
    return f"job:{job_id}"


def get_organizations(redis_client) -> list[dict]:
    raw = redis_client.get(ORGANIZATIONS_KEY)
    return json.loads(raw) if raw else []


def save_organizations(redis_client, orgs: list[dict]) -> None:
    redis_client.set(ORGANIZATIONS_KEY, json.dumps(orgs))


def get_data_sources(redis_client, tenant_id: str) -> list[dict]:
    raw = redis_client.get(_tenant_sources_key(tenant_id))
    return json.loads(raw) if raw else []


def save_data_sources(redis_client, tenant_id: str, sources: list[dict]) -> None:
    redis_client.set(_tenant_sources_key(tenant_id), json.dumps(sources))


def get_query_history(redis_client, tenant_id: str) -> list[dict]:
    raw = redis_client.get(_tenant_history_key(tenant_id))
    return json.loads(raw) if raw else []


def add_query_history(redis_client, tenant_id: str, item: dict) -> None:
    history = get_query_history(redis_client, tenant_id)
    history.insert(0, item)
    redis_client.set(_tenant_history_key(tenant_id), json.dumps(history[:100]))


def get_notifications(redis_client, tenant_id: str) -> list[dict]:
    raw = redis_client.get(_tenant_notifications_key(tenant_id))
    return json.loads(raw) if raw else []


def save_notifications(redis_client, tenant_id: str, items: list[dict]) -> None:
    redis_client.set(_tenant_notifications_key(tenant_id), json.dumps(items))


def add_notification(redis_client, tenant_id: str, item: dict) -> None:
    items = get_notifications(redis_client, tenant_id)
    items.insert(0, item)
    save_notifications(redis_client, tenant_id, items)


def get_active_jobs(redis_client) -> list[dict]:
    raw = redis_client.get(ACTIVE_JOBS_KEY)
    return json.loads(raw) if raw else []


def save_active_jobs(redis_client, jobs: list[dict]) -> None:
    redis_client.set(ACTIVE_JOBS_KEY, json.dumps(jobs))


def upsert_active_job(redis_client, job: dict) -> None:
    jobs = get_active_jobs(redis_client)
    jobs = [j for j in jobs if j.get("id") != job.get("id")]
    if job.get("status") == "running":
        jobs.insert(0, job)
    save_active_jobs(redis_client, jobs[:20])


def remove_active_job(redis_client, job_id: str) -> None:
    jobs = [j for j in get_active_jobs(redis_client) if j.get("id") != job_id]
    save_active_jobs(redis_client, jobs)


def create_job(redis_client, job: dict) -> str:
    job_id = job.get("id") or str(uuid.uuid4())
    job["id"] = job_id
    job.setdefault("createdAt", _now_iso())
    redis_client.set(_job_key(job_id), json.dumps(job), ex=3600)
    return job_id


def get_job(redis_client, job_id: str) -> dict | None:
    raw = redis_client.get(_job_key(job_id))
    return json.loads(raw) if raw else None


def update_job(redis_client, job_id: str, updates: dict) -> dict | None:
    job = get_job(redis_client, job_id)
    if not job:
        return None
    job.update(updates)
    redis_client.set(_job_key(job_id), json.dumps(job), ex=3600)
    return job


def increment_queries_today(redis_client) -> None:
    redis_client.incr(QUERIES_TODAY_KEY)


def get_platform_stats(redis_client) -> dict[str, Any]:
    orgs = get_organizations(redis_client)
    active_jobs = get_active_jobs(redis_client)
    queries_today = int(redis_client.get(QUERIES_TODAY_KEY) or 0)
    utilization = min(95, 40 + len(active_jobs) * 8 + len(orgs) * 2)
    return {
        "totalOrganizations": len(orgs),
        "activeJobs": len([j for j in active_jobs if j.get("status") == "running"]),
        "queriesToday": queries_today,
        "utilizationPercent": utilization,
    }


SUBSCRIPTION_PLANS = [
    {
        "id": "free",
        "name": "Free",
        "price": "$0",
        "period": "forever",
        "queryLimit": 100,
        "dataSourceLimit": 1,
        "features": [
            "100 queries per month",
            "1 data source",
            "CSV export only",
            "Email support",
        ],
    },
    {
        "id": "half_year",
        "name": "Half Year",
        "price": "$499",
        "period": "6 months",
        "queryLimit": 5000,
        "dataSourceLimit": 5,
        "highlighted": True,
        "features": [
            "5,000 queries per month",
            "Up to 5 data sources",
            "Excel, PDF & CSV export",
            "Priority support",
            "Query history (90 days)",
        ],
    },
    {
        "id": "year",
        "name": "Annual",
        "price": "$899",
        "period": "12 months",
        "queryLimit": 20000,
        "dataSourceLimit": 20,
        "features": [
            "20,000 queries per month",
            "Up to 20 data sources",
            "All export formats",
            "Dedicated support",
            "Unlimited query history",
            "Advanced analytics dashboard",
        ],
    },
]


def get_org_by_tenant(redis_client, tenant_id: str) -> dict | None:
    return next((o for o in get_organizations(redis_client) if o["id"] == tenant_id), None)


def get_subscription_reminders(redis_client, tenant_id: str) -> list[dict]:
    org = get_org_by_tenant(redis_client, tenant_id)
    if not org:
        return []
    plan = org.get("plan", "free")
    reminders = []
    if plan == "half_year":
        reminders.append(
            {
                "id": "r-1",
                "message": "Your Half-Year subscription expires soon. Renew to avoid service interruption.",
                "plan": "half_year",
                "expiresAt": "2026-09-06",
                "daysRemaining": 14,
            }
        )
    if plan == "free":
        reminders.append(
            {
                "id": "r-2",
                "message": "Free tier query limit: 80% used this month.",
                "plan": "free",
                "expiresAt": "2026-08-31",
                "daysRemaining": 8,
            }
        )
    return reminders
