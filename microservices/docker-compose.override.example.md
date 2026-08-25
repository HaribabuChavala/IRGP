# Microservices compose override example

Use the generated override file in this repo root:

- docker-compose.microservices.yml

Example:

```bash
docker compose -f docker-compose.microservices.yml up -d --build
```

This starts the shared platform services plus all 10 FastAPI microservices:

- auth-service
- user-management-service
- org-registration-service
- platform-admin-service
- org-portal-service
- subscription-service
- notification-service
- reminder-service
- data-source-service
- report-generation-service
```
