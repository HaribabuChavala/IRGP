# Instant Report Generation Platform - Microservices

This directory contains the concrete service-by-service layout for the platform, including the core product services and the supporting platform services that make the system production-ready.

## Service list

Core business services:
1. auth-service
2. user-management-service
3. org-registration-service
4. platform-admin-service
5. org-portal-service
6. subscription-service
7. notification-service
8. reminder-service
9. data-source-service
10. report-generation-service
11. ai-sql-service

Operational / platform services:
12. audit-service
13. scheduler-service
14. observability-service
15. export-service
16. billing-service

## Shared conventions

Each service follows the same Python FastAPI pattern:

- app/main.py
- app/config.py
- app/security.py
- app/db.py
- app/models.py
- app/schemas/*.py
- app/api/*.py
- app/services/*.py
- requirements.txt
- Dockerfile

## Shared platform dependencies

All services use:
- PostgreSQL
- Redis
- Keycloak
- OPA
- Docker-based local orchestration
- HTTP-based internal service calls
- Observability telemetry via OpenTelemetry / Prometheus / Grafana / OpenSearch

## Suggested startup order

1. auth-service
2. user-management-service
3. org-registration-service
4. platform-admin-service
5. org-portal-service
6. subscription-service
7. notification-service
8. reminder-service
9. data-source-service
10. report-generation-service
11. audit-service
12. scheduler-service
13. observability-service
14. export-service
15. billing-service

## Notes

This scaffold is intentionally service-oriented and separates business logic from supporting platform capabilities. The newer services include auditability, workflow scheduling, observability, export orchestration, and billing readiness.
