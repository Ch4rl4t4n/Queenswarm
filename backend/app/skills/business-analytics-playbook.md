---
name: business-analytics-playbook
description: Codex-style business analytics report — question to read-only fetch, analyst narrative, critic rubric, export staging. Use with business-analytics-report swarm template — NOT for mutating GA4/warehouse config or live export without operator approve.
version: 1.0.0
priority: 88
roles: [orchestrator, researcher, critic]
keywords: [analytics, business, report, ga4, sheets, warehouse, narrative, lineage, export, decision, metrics, dashboard]
source: queenswarm.love
reference_mode: false
references: [ga4-analytics-playbook, self-review-loop, operator-approval-gate]
---

# Business Analytics Playbook

Purpose: Turn one **business question** + date range into a **decision-ready report** with cited metrics, lineage, critic score ≥4/5, and simulate-first export staging.

## When to use

- Apps & Tools → Analytics workspace dispatch (`business-analytics-report` template)
- Weekly leadership deck or KPI review from GA4 + Sheets + warehouse read slots
- Operator asks _what changed, why it matters, what to do next_

## When NOT to use

- Mutating GA4 admin, BigQuery jobs, or warehouse DDL
- Exporting user-level PII or raw event streams
- Live Notion/Slides publish without operator approval after critic pass

## Connector order (read-only default)

1. **HiveMind** — recall prior reports, benchmarks, operator notes (always first for context)
2. **GA4 Data API** — via `ga4-analytics-playbook` (`get_metadata` → `run_report`)
3. **Google Sheets read** — mcp_invoke when spreadsheet ID provided (read-only scope)
4. **Warehouse MCP slot** — Databricks/Snowflake read-only query when configured
5. **Notion export staging** — simulate-only page payload after critic ≥4/5

Parallel fetch only when CostGovernor allows; **default sequential** (cheaper, clearer lineage).

## Workflow (max 7 steps)

1. **Frame** — restate business question, date range, dimensions, success criteria
2. **Fetch** — pull metrics per connector order; tag each row with `source`, `query`, `timestamp`
3. **Analyze** — deltas vs prior period, anomalies, confidence scores; HiveMind cross-check
4. **Narrate** — executive summary + chart specs in markdown; every claim cites a fetch artifact
5. **Critic** — `self-review-loop` rubric ≥4/5; block export if numbers or lineage missing
6. **Stage export** — Notion/Slides simulate payload only (`execution_mode: simulate`)
7. **Recipe** — save verified flow to Recipe Library when operator approves outcome

## Sub-agent handoff (one session, max 5 bees)

| Bee | Skill focus |
|-----|-------------|
| Analytics Supervisor | Steps 1 + orchestration |
| Data Fetch Bee | Step 2 + `ga4-analytics-playbook` |
| Analyst Bee | Step 3 |
| Narrative Bee | Step 4 |
| Critic Bee | Step 5 |

## Required gates

| Action | Gate |
|--------|------|
| Live Notion/Slides export | operator-approval-gate |
| Financial decision from metrics | real-money-risk-gate |
| Publish derived insights externally | social-simulate-first |
| Subjective report quality | self-review-loop · rubric ≥4/5 |

## Guardrails

- `execution_mode: simulate` default for all export lanes
- Read-only connectors only unless operator explicitly enables write scope
- Never invent metrics — flag `data_gap` when source unavailable
- Store `lineage` array on session context (connector · query · timestamp per section)
- Cost cap: sequential fetch; max 3 connector round-trips without supervisor re-approve

## Verification checklist

- [ ] Business question and date range documented in session goal
- [ ] Every cited number traceable to fetch artifact + lineage row
- [ ] Critic rubric score ≥4/5 recorded before export staging
- [ ] No PII in report body or export payload
- [ ] Export staged simulate-first; operator approve before live
