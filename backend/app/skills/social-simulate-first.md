---
name: social-simulate-first
description: Queues social posts in simulate mode before any live OAuth publish. Use when Instagram, X, TikTok, or Facebook content is ready — NOT for immediate live blast without approval gate.
version: 1.0.0
priority: 84
roles: [designer, orchestrator]
keywords: [social, publish, simulate, instagram, tiktok, facebook, queue, oauth]
source: queenswarm.love
---

# Social Simulate-First

Purpose: All social content flows through **publish queue simulate** before live.

## Workflow

1. Draft post pack (copy + media refs)
2. Insert publish queue with `mode: simulate`
3. Preview in Execution Studio Social Publish panel
4. Operator review batch
5. Flip to live only if `SOCIAL_PUBLISH_LIVE_ENABLED` + approval gate

## Multi-channel

- Tag channel + firm_id per post
- Respect module policy pack cooldown
- Trade→content bridge: optional draft from trading fills

## Guardrails

- OAuth tokens in vault only
- No auto-live on cron without operator flag
- Log every simulate → live transition
