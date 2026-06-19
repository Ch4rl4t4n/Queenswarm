---
name: community-engagement-playbook
description: Collect community threads, draft helpful replies with subtle brand fit, score with community-authenticity rubric, queue simulate publish — NOT live autopilot spam. Use for Reddit/forums/comment engagement after forager ingest or operator intent.
version: 1.0.0
priority: 86
roles: [researcher, designer, critic, orchestrator]
keywords: [community, reddit, forum, engagement, reply, authenticity, publish, simulate, najman, hivemind]
source: queenswarm.love
---

# Community Engagement Playbook (POS-CE)

Purpose: **Collect → compose → commit (HITL)** — agents find opportunities and draft replies; operator approves before any public post.

## When to use

- Forager tagged rows: `engagement-candidate`, `community-intel`
- Marketing four-lane digest step (max 3 draft replies)
- Operator procedure `/community-engage` or Data Monitor community niche
- **NOT** for: cold DMs, mass posting, bypassing platform rules

## Workflow (max 7 steps)

1. **Recall** — HiveMind + curated BRAND/SOUL; load `community_engagement` caps from session context
2. **Select** — pick threads where you can add genuine value (question/help intent, not locked/flame wars)
3. **Research** — read thread context; note subreddit/forum tone (formal, casual, CZ/SK)
4. **Draft** — helpful answer first; at most one subtle product mention if naturally relevant
5. **Closed review** — rubric `community-authenticity` via closed-review-loop (min 4/5)
6. **Queue** — publish queue **simulate**; tag deliverable `community-reply-draft`
7. **Handoff** — operator approves in Tasks / publish queue; **never** live post without approval gate

## Output shape (per draft)

```yaml
platform: reddit | forum | x_reply
thread_url: https://...
community: r/subreddit or forum name
intent_detected: question | recommendation | troubleshooting
draft_reply: |
  (full text, ready to paste or connector publish)
promo_level: none | subtle | n/a
rubric_template_id: community-authenticity
simulate_only: true
operator_approve_required: true
```

## Combine with

| Module | Role |
|--------|------|
| Forager RSS (Reddit `.rss`) | Collect new threads |
| Data Monitor wizard | Spawn community monitor from intent |
| marketing-campaign-playbook | Same brand voice for Najman / firm_id |
| closed-review-loop | Tone + anti-spam gate |
| operator-approval-gate | Live publish block |
| Goldmine alerts → Kanban | Triage high-signal threads |
| social-intel-evaluator | Inbound intel only — do not reuse for outbound spam |

## Guardrails

- **Value before promo** — if draft fails helpfulness, rewrite without product mention
- **Max drafts** — respect `max_draft_replies_per_digest` (default 3)
- **Max live** — respect `max_live_posts_per_day` (default 0 = simulate only)
- **No** deleted tests / weakened checks to pass rubric (LN2)
- **No** fabricated personal experience ("I used X for years…") unless in curated memory
- **Simulate-first** — pollen only after operator-approved outcome

## Stop conditions

- Same rubric failure twice on one thread → `needs_input` for operator
- Negative sentiment / mod removal risk → skip + log reason
- Budget / LOOP2 max turns → halt with summary for operator
