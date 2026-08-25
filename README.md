# Instant Report Generation Platform

Free/local Docker lab for Step 2 of the architecture.

Components:
- Traefik: reverse proxy, routing and local load-balancing
- Keycloak: OAuth 2.0 / OIDC / authentication / RBAC
- OPA: ABAC policy engine
- PostgreSQL: Keycloak database + future application state
- Redis: future cache/job state/pub-sub
- FastAPI: sample backend
- Next.js UI: Instant Report Generation Platform frontend

## Prerequisites

Windows 11 + Docker Desktop using WSL 2.

Check:
docker version
docker compose version
wsl --version

## Local startup

### 1. Copy the environment template

Copy the example environment file before starting the stack:

copy .env.example .env

Then review and adjust values as needed.

For deployment-like or CI/CD use, also keep a production template ready:

copy .env.production.example .env.production

This file is intended for environment injection and secret-managed deployment, not a checked-in production secret file.

Run production preflight validation before deploy:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\production-preflight.ps1 -EnvFile .env.production
```

```bash
./scripts/production-preflight.sh .env.production
```

See `PRODUCTION_SUPPORT.md` for the production support baseline and release checklist.

### 2. Ensure *.localhost aliases exist

The routed services are exposed through Traefik using hostnames such as `report.localhost`, `app.localhost`, `auth.localhost`, and `audit.localhost`.

Windows:

powershell -ExecutionPolicy Bypass -File .\scripts\ensure-local-hosts.ps1

Linux/macOS:

sudo ./scripts/ensure-local-hosts.sh

### 3. Start the full verified stack

Use the full merged compose configuration that includes the base services and the full microservice catalog:

docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.microservices.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.microservices.yml ps

This is the stack configuration that has been verified to bring up the API, UI, Keycloak, Postgres, Redis, Traefik, and the full microservice set.

### 4. One-command startup and verification

The project includes a helper that performs startup plus verification:

powershell -ExecutionPolicy Bypass -File .\scripts\Start-Stack-And-Verify.ps1

This script starts the stack, ensures the localhost aliases exist, waits for readiness, and then runs the health checks.

### 5. Verify service health and endpoints

Check container health:

docker compose ps

Quick local verification through the helper scripts:

powershell -ExecutionPolicy Bypass -File .\scripts\Check-Microservices.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\Smoke-Test.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\status-all.ps1

The last script is the current canonical end-to-end health check. It should report `All configured services are responding.` when the stack is healthy.

### Seed demo data (development only)

Once the database is running, you can load a small demo dataset for organizations, users, reports, and reminders:

powershell -ExecutionPolicy Bypass -File .\scripts\seed-demo-data.ps1

or

./scripts/seed-demo-data.sh

This creates a few realistic example records for local UI testing and API validation.

See also the URL list in `scripts/expected-service-urls.md`.

## URLs

Traefik dashboard: http://localhost:8088/dashboard/
Keycloak: http://localhost:8081/
Keycloak admin: http://localhost:8081/admin/
API: http://report.localhost/health
UI (Docker/Traefik): http://app.localhost
Auth: http://auth.localhost/health
Users: http://users.localhost/health
Organizations: http://orgs.localhost/health
Platform admin: http://platform-admin.localhost/health
Portal: http://portal.localhost/health
Subscriptions: http://subscriptions.localhost/health
Notifications: http://notifications.localhost/health
Reminders: http://reminders.localhost/health
Data sources: http://datasources.localhost/health
Reports: http://reports.localhost/health
Audit: http://audit.localhost/health
Scheduler: http://scheduler.localhost/health
Observability: http://observability.localhost/health
Export: http://export.localhost/health
Billing: http://billing.localhost/health

UI (local dev): http://localhost:3000

## AI SQL generation (phase 1)

When a user clicks Generate on the Reports screen, the API now calls a separate microservice: `ai-sql-service`.

The `ai-sql-service` runs an ADK-style SQL pipeline:

1. Schema discovery from the selected data source metadata.
2. Semantic planning from user prompt.
3. SQL generation for the source dialect (Oracle, Teradata, Hive, Excel/SQLite fallback).
4. SQL safety validation (SELECT-only, table allow-list, dangerous operation block-list).
5. Cost estimate + lightweight PII detection.

Strict validator rules are enabled by default:

1. Wildcard selection is denied (`SELECT *` and `table.*`).
2. Row limits are enforced and capped by `MAX_SQL_LIMIT`.
3. Tables must be in explicit per-tenant allow-lists (`TENANT_TABLE_ALLOWLIST_JSON`).

For local development, `ai-sql-service` runs with a built-in fallback implementation.
To connect a remote Google ADK service behind `ai-sql-service`, set these environment variables:

- GOOGLE_ADK_AGENT_URL
- GOOGLE_ADK_AGENT_API_KEY
- MAX_SQL_LIMIT
- DENY_STAR_SELECT
- ENFORCE_ROW_LIMIT
- REQUIRE_TENANT_ALLOWLIST
- TENANT_TABLE_ALLOWLIST_JSON

Current local default wiring uses a Dockerized mock ADK service:

- `GOOGLE_ADK_AGENT_URL=http://google-adk-agent:8001/agent`
- `GOOGLE_ADK_AGENT_API_KEY=local-adk-test-key`

Start local ADK + SQL services:

```powershell
docker compose up -d --build google-adk-agent ai-sql-service
```

Validate ADK and SQL routes through Traefik:

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost/health" -Headers @{ Host="adk.localhost" }
Invoke-RestMethod -Method Get -Uri "http://localhost/health" -Headers @{ Host="aisql.localhost" }
```

Switch to a real Google ADK backend (same integration path, no code changes):

```powershell
$env:GOOGLE_ADK_AGENT_URL = "https://your-real-adk-endpoint/agent"
$env:GOOGLE_ADK_AGENT_API_KEY = "your-real-adk-api-key"
docker compose up -d --build ai-sql-service
```

Direct Gemini API is also supported. Use a Google Generative Language URL and model name:

```powershell
$env:GOOGLE_ADK_AGENT_URL = "https://generativelanguage.googleapis.com/v1beta"
$env:GOOGLE_ADK_AGENT_API_KEY = "your-google-ai-studio-key"
$env:GOOGLE_GEMINI_MODEL = "gemini-3.6-flash"
docker compose up -d --build ai-sql-service
```

Store the Google API key in Vault (KV v2) and let `ai-sql-service` read it at runtime:

```powershell
$vaultBody = @{ data = @{ GOOGLE_ADK_AGENT_API_KEY = "your-google-ai-studio-key" } } | ConvertTo-Json -Depth 4
Invoke-RestMethod -Method Post -Uri "http://localhost:8200/v1/secret/data/report-platform" -Headers @{ "X-Vault-Token" = "dev-root-token" } -ContentType "application/json" -Body $vaultBody
```

Then keep these env values set for the service:

- `VAULT_ADDR=http://vault:8200`
- `VAULT_TOKEN=dev-root-token`
- `VAULT_SECRET_PATH=secret/data/report-platform`
- `VAULT_GOOGLE_ADK_API_KEY_FIELD=GOOGLE_ADK_AGENT_API_KEY`

For full mock endpoint examples, see `microservices/google-adk-agent/README.md`.

The generated SQL is returned in the report job stream and displayed in the UI chat output.

Direct health check:

- http://aisql.localhost/health

## Local Oracle and Teradata lab data sources

For datasource onboarding and report testing in Docker, this stack now includes:

1. Oracle Free test database (`oracle` service)
2. Teradata lab test database (`teradata-lab` service, PostgreSQL-backed for local compatibility)

Start both services:

```powershell
docker compose up -d --build oracle teradata-lab api
```

Use these datasource settings in the UI:

Oracle (real Oracle protocol)

- Type: `oracle`
- Host: `oracle`
- Port: `1521`
- Database/Service: `FREEPDB1`
- Username: `report_ro`
- Password: `ReportReadOnly123`
- Access mode: `read`

Seeded Oracle tables:

- `report_owner.customers`
- `report_owner.sales_orders`

Teradata lab (local test mode)

- Type: `teradata`
- Host: `teradata-lab`
- Port: `1025`
- Database: `teradata_lab`
- Username: `td_readonly`
- Password: `TdReadOnly123`
- Access mode: `read`

Seeded Teradata lab tables:

- `public.customers`
- `public.sales_orders`

Note: There is no official self-contained Teradata Vantage Docker image for simple local use. The `teradata-lab` service provides a Docker-only compatibility path for application testing in this lab.

Keycloak admin:
username = admin
password = change-me-admin

Realm:
report-platform

Demo user:
report-user
password = report-user-password

Platform admin:
platform-admin
password = platform-admin-password

Organization admin:
org-admin
password = org-admin-password

## UI development (without Docker)

cd ui
npm install
npm run dev

See `ui/README.md` for module routes and environment variables.

## ABAC test

Allowed:
curl.exe -X POST http://report.localhost/api/v1/policy/check -H "Content-Type: application/json" -d "{"user":{"roles":["REPORT_USER"],"tenant_id":"hsbc","region":"UK"},"resource":{"tenant_id":"hsbc","region":"UK"},"action":"read"}"

Denied:
curl.exe -X POST http://report.localhost/api/v1/policy/check -H "Content-Type: application/json" -d "{"user":{"roles":["REPORT_USER"],"tenant_id":"hsbc","region":"US"},"resource":{"tenant_id":"hsbc","region":"UK"},"action":"read"}"

Expected:
allowed=true for the first
allowed=false for the second

## Stop

docker compose down

Delete development data too:
docker compose down -v

## Next steps

1. Add JWT validation in FastAPI using Keycloak JWKS.
2. Extract user/tenant/roles from the verified JWT.
3. Call OPA for dataset-level ABAC.
4. Propagate requestId, traceId, userId and tenantId.
5. Add SSE for report progress.
6. Add Redis Pub/Sub for job events.
7. Add secrets management.
8. Add Cloudflare after the local stack works.

This is a development lab. Do not use the demo passwords, HTTP-only configuration, or development-mode Keycloak directly in production.
