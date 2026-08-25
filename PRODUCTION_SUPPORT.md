# Production Support Baseline

This document defines the minimum production-support posture for this project.

## 1. Secrets and configuration

1. Do not run with default development values.
2. Use `.env.production.example` as template and inject real values via CI/CD secrets.
3. Run a preflight check before deploy:
   - PowerShell: `powershell -ExecutionPolicy Bypass -File ./scripts/production-preflight.ps1 -EnvFile .env.production`
   - Bash: `./scripts/production-preflight.sh .env.production`

## 2. Deployment

1. Build and deploy from pinned repository commit.
2. Start stack with production env file:
   - `docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.microservices.yml up -d --build`
3. Verify health:
   - `docker compose ps`
   - `powershell -ExecutionPolicy Bypass -File ./scripts/status-all.ps1`

## 3. Runtime checks

1. Identity and auth:
   - Keycloak realm is reachable and JWKS URL is valid.
2. Vault:
   - API token configured (`VAULT_TOKEN`) and KV path reachable.
3. Data source onboarding:
   - Test Connection must succeed before Save.
   - Credentials are written to Vault, not datasource metadata.
4. AI SQL controls:
   - `DENY_STAR_SELECT=true`
   - `ENFORCE_ROW_LIMIT=true`
   - `REQUIRE_TENANT_ALLOWLIST=true`

## 4. Operational guardrails

1. Use dedicated read-only datasource accounts.
2. Rotate credentials periodically in source systems and Vault.
3. Keep backups for Postgres and Vault data.
4. Enable centralized log collection for API and microservices.
5. Maintain incident playbook for:
   - Keycloak outage
   - Vault outage
   - Redis outage
   - Postgres outage

## 5. Release checklist

1. Preflight script passes.
2. Lint/test/compile checks pass.
3. Health checks pass after deploy.
4. Sample datasource test-and-save works.
5. Sample report generation works end-to-end.

## 6. CI production gate

GitHub Actions workflow: `.github/workflows/production-gate.yml`

It enforces:

1. Production template policy check (`scripts/validate-production-template.py .env.production.example`)
2. UI lint (`npm run lint` in `ui`)
3. Backend compile and AI SQL service tests
