---
name: operator-approval-gate
description: Gates live, financial, and publish actions until operator explicitly approves. Use when a workflow touches real money, live publish, production deploy, or irreversible writes — NOT for read-only research or simulate-first drafts.
version: 1.0.0
priority: 98
roles: [orchestrator, critic, researcher, coder]
keywords: [approve, approval, gate, live, financial, publish, operator, simulate, needs_input, human]
source: queenswarm.love
---

# Operator Approval Gate

Purpose: Enforce **human-in-the-loop** before any action that spends money, publishes publicly, or mutates production.

## When to use

- Live trading execution (after paper track record)
- Social publish (`SOCIAL_PUBLISH_LIVE_ENABLED`)
- Connector invoke with `risk_tier: financial` or `publish`
- Queen Maintainer merge (operator merges PR — agent stops at open PR)
- Innovation Lab → implement queue

## When NOT to use

- Simulate-first drafts in publish queue
- Paper trading fills
- HiveMind read / research ingest
- Internal Notion drafts

## Gate checklist

1. **Simulate** — run applicable simulation; attach evidence
2. **Risk tier** — label `read | write | publish | financial`
3. **Policy pack** — module cooldown, spend cap, time limit respected
4. **Operator signal** — explicit approve in UI, Telegram, or session `needs_input` resolution
5. **Audit** — log user, action, target, timestamp

## Output format

```yaml
gate_status: pending | approved | rejected
risk_tier: ...
simulation_ref: ...
operator_required: true
blocked_reason: null | string
```

## Guardrails

- Never bypass gate via raw API if `requires_approval: true` on capability
- Default `execution_mode: simulate`
- Pollen only after verified outcome post-approval
