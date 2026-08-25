# Google ADK Agent Mock (Local Dev)

This service is a local mock backend for the AI SQL pipeline.

## Start

From the repo root:

```powershell
docker compose up -d --build google-adk-agent ai-sql-service
```

## Health checks

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost/health" -Headers @{ Host="adk.localhost" }
Invoke-RestMethod -Method Get -Uri "http://localhost/health" -Headers @{ Host="aisql.localhost" }
```

Expected:

- ADK route returns: `{"status":"ok","service":"google-adk-agent"}`
- AI SQL route returns: `{"status":"ok","service":"ai-sql-service"}`

## Test ADK endpoint directly through Traefik

```powershell
$body = @{
  task = "generate_sql"
  prompt = "Show revenue by region"
  dialect = "oracle"
  tenant_id = "tenant-demo"
  data_source = @{ id = "ds-1"; name = "Oracle Sales"; type = "oracle"; database = "testing" }
  schema_context = @{ tables = @("testing.sales_orders") }
  policy = @{ allowed_tables = @("testing.sales_orders") }
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri "http://localhost/agent" -Headers @{ Host="adk.localhost"; Authorization="Bearer local-adk-test-key" } -ContentType "application/json" -Body $body
```

## Test end-to-end SQL generation

```powershell
$body = @{
  prompt = "Show revenue by region"
  tenant_id = "tenant-demo"
  data_source = @{ id = "ds-1"; name = "Oracle Sales"; type = "oracle"; database = "testing" }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post -Uri "http://localhost/generate-sql" -Headers @{ Host="aisql.localhost" } -ContentType "application/json" -Body $body
```

When the mock path is active, the response includes `provider: "google-adk-remote"`.

## Switch to real Google ADK URL (same integration path)

Set environment variables and restart only `ai-sql-service`:

```powershell
$env:GOOGLE_ADK_AGENT_URL = "https://your-real-adk-endpoint/agent"
$env:GOOGLE_ADK_AGENT_API_KEY = "your-real-adk-api-key"
docker compose up -d --build ai-sql-service
```

Or set the same values in your `.env` file.

The AI SQL service still calls `GOOGLE_ADK_AGENT_URL` with Bearer auth, so no app code changes are required.
