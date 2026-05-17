# Queenswarm External API (Tenant Scoped)

This document describes the external API layer introduced in Phase 10.4 for project integrations.

## Authentication

- Header: `X-Queenswarm-External-Key: qs_ep_...`
- Alternative: `Authorization: Bearer qs_ep_...`
- Keys are scoped to one external project and tenant.

## Base Path

- Internal API surface: `/api/v1/ext-api/v1`

## Endpoints

### `GET /scope`

Returns current API key scope:

- `project_id`
- `project_slug`
- `project_kind`
- `tenant_id`
- `api_key_id`
- `permissions`

### `POST /projects/{project_slug}/run`

Execute one external action through the project manager lane.

Request body:

```json
{
  "action": "string",
  "payload": {}
}
```

Response includes:

- `audit_id`
- `project_slug`
- `latency_ms`
- `cost_usd`
- `ok`
- `result`

## Permission model

- Keys use scoped permissions (for example: `run`, `mcp:call`, `trading:live`, or `*`).
- Tenant mismatch between key and project is denied.
- Slug mismatch between key scope and requested project is denied.

## Notes

- This is a dedicated external-consumer layer separate from dashboard operator routes.
- Billing/usage telemetry for external calls is tracked and included in tenant usage dashboards.
