---
name: queenswarm-operator-gate
description: Queenswarm operator daily ritual and approval gates for marketing, trading, and self-improvement loops. Use when working in Queenswarm repo on swarm config, harness, Innovation Lab, or deploy decisions — NOT for unrelated projects.
---

# Queenswarm Operator Gate

## Daily ritual (15 min)

1. **Agent OS** — merge overnight behavioral proposals into harness
2. **Innovation Lab** — approve/reject 1–3 improvement proposals
3. **Publish queue** — review simulate social packs
4. **Trading cockpit** — review paper P&L digest
5. **Evening** — Dump & Sleep for dreaming feed

## Before live actions

- Marketing live publish → `SOCIAL_PUBLISH_LIVE_ENABLED` + explicit approve
- Trading live → `real-money-risk-gate` + 4+ weeks paper track record
- Deploy prod → `./scripts/whole-app-ui-release-gate.sh` then `./scripts/deploy-prod.sh`

## Self-improvement loop

Research → HiveMind verify → Innovation Lab → approve → Queen Maintainer PR → merge → recipe

## Key paths

- Backend skills: `backend/app/skills/*.md`
- Harness template: `docs/curated_memory_templates/operator_harness_instructions.md.example`
- Readiness gate: `./scripts/audit-swarm-readiness-gate.sh`

## Guardrails

- Never commit `.env*` secrets
- Maintainer PR-only — never direct write to main
- Simulate-first always default
