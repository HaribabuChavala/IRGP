# Expected service URLs

This project exposes the following endpoints locally through Traefik and direct ports:

## Core infrastructure
- Traefik dashboard: http://localhost:8088/dashboard/
- Keycloak: http://localhost:8081/
- Keycloak admin: http://localhost:8081/admin/
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Vault: http://localhost:8200
- OPA: http://localhost:8181

## Primary app URLs
- API: http://report.localhost
- UI (Docker/Traefik): http://app.localhost
- UI (local Next.js): http://localhost:3000

## Microservice health endpoints
- Auth: http://auth.localhost/health
- User management: http://users.localhost/health
- Org registration: http://orgs.localhost/health
- Platform admin: http://platform-admin.localhost/health
- Org portal: http://portal.localhost/health
- Subscription: http://subscriptions.localhost/health
- Notification: http://notifications.localhost/health
- Reminder: http://reminders.localhost/health
- Data source: http://datasources.localhost/health
- Report generation: http://reports.localhost/health
- Audit: http://audit.localhost/health
- Scheduler: http://scheduler.localhost/health
- Observability: http://observability.localhost/health
- Export: http://export.localhost/health
- Billing: http://billing.localhost/health

## Common app checks
- Report endpoint: http://report.localhost/api/v1/security/test
- Keycloak realm: http://localhost:8081/realms/report-platform
