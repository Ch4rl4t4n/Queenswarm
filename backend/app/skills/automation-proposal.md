---
version: "1.0"
priority: 0.88
roles:
  - supervisor
  - researcher
  - critic
keywords:
  - automation
  - workflow
  - routine
  - recipe
  - n8n
  - zapier
  - webhook
  - cron
  - execution studio
---

# Automation Proposal (native-first)

Use when an agent or operator asks to automate a recurring process, connect apps, or
"build a workflow". **Prefer Queenswarm-native primitives before external workflow tools.**

## Decision tree (strict order)

1. **SupervisorRoutine + Celery cron** — recurring department work (Sales waterfall, Marketing cycle).
   - Use when: same goal on a schedule, swarm can run in simulate/durable mode.
2. **Recipe Library replay** — verified workflow already exists from a simulate run.
   - Use when: a first-run playbook succeeded and should repeat with same guardrails.
3. **Forager source + intelligence scan** — ingest RSS/API/docs on schedule into HiveMind.
   - Use when: automation is primarily research / signal collection.
4. **Execution Studio + MCP connector** — real outbound actions (Gmail, Notion, GitHub, Composio).
   - Use when: automation must write/send/publish; always default to **simulate** first.
5. **Webhook / notification trigger** — operator ping on completion or approval gate.
   - Use when: human must approve before live execution.
6. **External workflow hub (n8n, Zapier, Make)** — **last resort only**.
   - Use when: steps span many SaaS apps with no MCP path AND native options were rejected in writing.

## Required proposal output

When proposing automation, emit:

| Field | Content |
|-------|---------|
| `native_path` | Which steps 1–5 cover the need (be specific: routine name, recipe id, connector slugs) |
| `external_path` | Only if native path insufficient — name tool + why |
| `schedule` | Cron or event trigger (UTC), expected runtime |
| `execution_mode` | `simulate` default; `live` only with approval gates |
| `verification` | How simulate confirms success before user sees results |
| `risk` | low / medium / high + guardrails dict |

## Anti-patterns (never propose without justification)

- Jumping straight to n8n/Zapier when a **Routine + Recipe** suffices.
- Live financial or destructive actions without Execution Studio approval.
- Monolithic "one agent does everything" instead of department swarm + handoff.
- Raw cron scripts outside Celery beat / supervisor routine tick.

## n8n as optional marketplace tool

If native path is insufficient, agents may **propose** installing an n8n webhook template from
marketplace (operator approval required). Document:

- Trigger (webhook URL Queenswarm calls)
- Payload schema
- Fallback if n8n unreachable (queue + notify operator)

Never store n8n credentials in prompts or logs.
