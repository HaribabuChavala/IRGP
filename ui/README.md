# Instant Report Generation Platform — UI

Next.js + React frontend for the Instant Report Generation Platform, integrated with **Keycloak OIDC** and the **FastAPI** backend.

## Tech Stack

- **Next.js 16** (App Router)
- **React 19**
- **TypeScript**
- **Tailwind CSS 4**
- **Keycloak JS** (OIDC authentication)
- **Lucide React** (icons)

## Prerequisites

1. Start the backend lab from the repo root:

```bash
docker compose up -d --build
```

2. Add to your hosts file (if not already present):

```
127.0.0.1 report.localhost
127.0.0.1 app.localhost
```

3. Copy environment file:

```bash
cp .env.local.example .env.local
```

## Getting Started

```bash
cd ui
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and sign in with Keycloak.

## Demo Accounts (Keycloak)

| Username | Password | Role |
|----------|----------|------|
| `platform-admin` | `platform-admin-password` | Platform Admin |
| `org-admin` | `org-admin-password` | Organization Admin |
| `report-user` | `report-user-password` | Organization User |

Realm: `report-platform` · Client: `report-platform-ui`

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | `http://report.localhost` | FastAPI backend (Traefik) |
| `NEXT_PUBLIC_KEYCLOAK_URL` | `http://localhost:8081` | Keycloak server |
| `NEXT_PUBLIC_KEYCLOAK_REALM` | `report-platform` | OIDC realm |
| `NEXT_PUBLIC_KEYCLOAK_CLIENT_ID` | `report-platform-ui` | OIDC public client |

## Module Routes

| Module | Route |
|--------|-------|
| Login | `/login` → Keycloak OIDC |
| Auth callback | `/auth/callback` |
| Platform Admin Dashboard | `/admin/dashboard` |
| Register Organization | `/admin/organizations/register` |
| Register Users | `/admin/users/register` |
| User Dashboard | `/dashboard` |
| Instant Reports (SSE chat) | `/reports` |
| Data Sources | `/data-sources` |
| Subscriptions | `/subscriptions` |
| Notifications | `/notifications` |
| Reminders | `/reminders` |

## API Integration

All data is loaded from FastAPI at `NEXT_PUBLIC_API_BASE_URL`:

- Platform stats & organizations → `/api/v1/platform/*`
- Org dashboard, data sources, notifications → `/api/v1/org/*`
- Report generation → `POST /api/v1/reports/generate`
- SSE progress → `GET /api/v1/reports/jobs/{id}/stream`
- Export → `GET /api/v1/reports/jobs/{id}/export?format=csv|excel|pdf`

Requests include `Authorization: Bearer <keycloak_access_token>`.

## Keycloak Realm Update

The realm import adds client `report-platform-ui`, roles, protocol mappers (`tenant_id`, `region`, `organization_name`), and demo users.

If Keycloak was already running, re-import the realm:

```bash
docker compose down
docker volume rm instant-report-generation-platform_postgres-data   # only if you need a clean Keycloak DB
docker compose up -d --build
```

Or delete the Keycloak DB volume and restart so `--import-realm` runs again.

## Docker UI Service

```bash
docker compose up -d ui
```

UI: [http://app.localhost](http://app.localhost) or [http://localhost:3000](http://localhost:3000)

## Regenerate `package-lock.json` for Docker (npm version match)

The UI Docker image uses **Node 22 / npm 10**. If you use a newer local Node/npm, regenerate the lockfile inside the same image before `docker compose build ui`.

**PowerShell** (from repo root):

```powershell
docker run --rm -v "${PWD}/ui:/app" -w /app node:22-alpine npm install
```

**Command Prompt**:

```cmd
docker run --rm -v "%cd%\ui:/app" -w /app node:22-alpine npm install
```

**Absolute path** (works everywhere):

```powershell
docker run --rm -v "C:/Projects/access-security-lab/ui:/app" -w /app node:22-alpine npm install
```

## Scripts

- `npm run dev` — Development server
- `npm run build` — Production build
- `npm run start` — Production server
- `npm run lint` — ESLint
