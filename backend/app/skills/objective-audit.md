---
version: 1.0.0
priority: 90
roles:
  - supervisor
  - critic
  - evaluator
keywords:
  - objective audit
  - guardrails
  - approval gate
  - pricing safety
  - live action safety
  - compliance
reference_mode: true
---

# Objective Audit

Use before running a new agent objective, business simulation, pricing recommendation, growth workflow, or external action plan.

## Purpose

Catch unsafe goals before they become emergent behavior. The audit rewrites risky objectives into simulate-first, operator-approved, trust-preserving objectives.

## Checks

- live action without approval
- autonomous pricing or dynamic pricing without approval
- supracompetitive pricing patterns
- spammy or manipulative growth
- missing customer trust constraint
- missing audit log / approval gate

## CLI Flow

```bash
python scripts/objective_guardrail_auditor.py \
  --name "gumroad launch advisor" \
  --objective "recommend a sustainable Gumroad launch price after simulation" \
  --guardrail "approval gate before live changes" \
  --guardrail "preserve customer trust"
```

Outputs are written under `exports/guardrail-audits/`.

## Rule

If verdict is `blocked`, do not execute. Rewrite the objective, add guardrails, and re-audit first.
