# Developer Docker Setup and Minimal Verification

This guide gives a clean, developer-friendly flow to run the full platform in Docker and verify that all core services are working, including Oracle and Teradata internal test databases.

## 1) Prerequisites

- Docker Desktop running (WSL2 backend on Windows).
- PowerShell terminal at project root.
- Local host aliases configured (the provided script will do this).

Quick checks:

```powershell
docker version
docker compose version
```

## 2) Start the full stack

From project root:

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.microservices.yml up -d --build
```

Recommended helper command:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Start-Full-Stack.ps1
```

If the stack was previously interrupted or shows inconsistent network errors, do a clean reset:

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.microservices.yml down --remove-orphans
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.microservices.yml up -d
```

Or with helper scripts:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Stop-Full-Stack.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\Start-Full-Stack.ps1
```

## 3) Ensure localhost hostnames

Run as Administrator once:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\ensure-local-hosts.ps1
```

## 4) Minimal test case for all services

Use the one-command minimal test runner:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Minimal-Service-Test.ps1
```

Start and verify in one command:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Start-Full-Stack.ps1 -Verify
```

What this validates:

- Every routed service health URL responds through Traefik.
- Oracle database is reachable with readonly credentials and seeded tables are queryable.
- Teradata-lab database is reachable with readonly credentials and seeded tables are queryable.

Expected success line:

- Minimal test passed: all routed services responded and DB seeded data is accessible.

## 5) Internal DB test settings for datasource onboarding

Use these values in the UI datasource registration page.

### Oracle

- Type: oracle
- Host: oracle
- Port: 1521
- Service: FREEPDB1
- Username: report_ro
- Password: ReportReadOnly123
- Access mode: read

Seeded Oracle tables:

- report_owner.customers
- report_owner.sales_orders

### Teradata lab (Docker internal compatibility mode)

- Type: teradata
- Host: teradata-lab
- Port: 1025
- Database: teradata_lab
- Username: td_readonly
- Password: TdReadOnly123
- Access mode: read

Seeded Teradata-lab tables:

- public.customers
- public.sales_orders

## 6) Useful checks during development

Container status:

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.microservices.yml ps
```

Canonical health check:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\status-all.ps1
```

Key endpoints:

- Traefik dashboard: http://localhost:8088/dashboard/
- Keycloak realm: http://localhost:8081/realms/report-platform
- API health: http://report.localhost/health
- UI: http://app.localhost

## 7) Common issues and quick fixes

- One or more host URLs unavailable:
  - Run the clean reset commands in section 2.
- Keycloak realm temporarily unavailable right after startup:
  - Wait 15-30 seconds and rerun the minimal test.
- Oracle slow startup:
  - Allow extra warmup time on first run.

This document is intended for daily local developer use and internal integration testing.
