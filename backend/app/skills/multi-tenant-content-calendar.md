---
name: multi-tenant-content-calendar
description: Manages content calendars for multiple firms/brands from a single swarm. Use when scheduling posts, emails, or campaigns across tenants — NOT for single-brand one-off drafts.
version: 1.0.0
priority: 82
roles: [designer, researcher, orchestrator]
keywords: [calendar, schedule, multi-tenant, firm, content, notion, cron]
source: queenswarm.love
---

# Multi-Tenant Content Calendar

Purpose: One marketing swarm serves **multiple firms** with isolated calendars and brand voices.

## Data model (Notion or internal)

| Field | Purpose |
|-------|---------|
| `firm_id` | Tenant key |
| `scheduled_at` | UTC timestamp |
| `channel` | ig / x / tiktok / email |
| `status` | draft / queued / simulate / live |
| `asset_ref` | Link to draft content |

## Workflow

1. Load firm list from curated memory or Notion
2. Generate week-ahead slots per firm (no cross-firm mixing)
3. Fill drafts via marketing-campaign-playbook
4. Queue simulate publishes
5. Operator batch-approve live window

## Guardrails

- Max posts per firm per day (policy pack)
- Cooldown between live publishes
- firm_id required on every row
