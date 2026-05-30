---
name: email-drip-sequences
description: Builds multi-step email nurture sequences per firm via Gmail or Resend. Use when e-shop or marketing funnels need drip campaigns — NOT for live bulk send without approval.
version: 1.0.0
priority: 77
roles: [designer, orchestrator]
keywords: [email, drip, sequence, gmail, resend, nurture, funnel]
source: queenswarm.love
---

# Email Drip Sequences

Purpose: Multi-step email sequences tagged by `firm_id` and funnel stage.

## Workflow

1. Load segment from Notion or HiveMind
2. Draft sequence (3–7 emails) with spacing rules
3. Stage as Gmail/Resend **drafts** (simulate)
4. Operator batch-approve live window
5. Track opens/clicks if connector supports read

## Guardrails

- firm_id on every message
- Unsubscribe link required before live
- Max sends per day (policy pack)
