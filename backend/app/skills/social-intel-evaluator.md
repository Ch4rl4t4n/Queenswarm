---
name: social-intel-evaluator
description: Evaluates scraped YouTube/X signals for swarm tech fit and easy side-business angles. Use after social intel ingest — score, filter, write HiveMind insights only for keep verdicts.
version: 1.0.0
priority: 82
roles: [researcher, critic, orchestrator]
keywords: [social intel, youtube, x, twitter, hivemind, business ideas, tech signals, forager]
source: queenswarm.love
---

# Social Intel Evaluator

Purpose: Turn raw scraped posts into **verified, actionable HiveMind insights** — tech opportunities + lightweight business ideas Queenswarm can execute.

## When to use

- After forager scrape ingest (`forager:youtube`, `forager:x`)
- Daily delta review (new videos/tweets since last cursor)
- Operator asks to evaluate a channel batch

## Workflow (3–7 steps)

1. **Search HiveMind first** — avoid duplicate insights on same URL/video/tweet id.
2. **Summarize** each item in 3 bullets (what changed, who said it, why it matters).
3. **Grok truth arbiter (mandatory)** — for EVERY factual bullet run ONE cross-check
   (`xai/grok-3-mini`). Drop bullets with `verdict=false`. Keep only `true+high/medium`
   or `partial+medium` with explicit caveat in the insight.
4. **Tech fit score (1–5)** — can Queenswarm execute with existing connectors/skills/recipes?
5. **Business angle score (1–5)** — easy side offer swarm could ship in ≤14 days?
6. **Verdict**: `keep` | `archive` | `follow-up` — only `keep` + `follow-up` after Grok pass.
7. **Write insight** (simulate Notion or Knowledge) with tag `hivemind-candidate`, `social-intel`.
   Remove tag `pending-grok-verification` from promoted items.
8. **Emit pollen** only after simulation + Grok verification gate passes.

## Output shape

```markdown
Title: [INSIGHT] <topic — 5-9 words>
Tags: hivemind-candidate, social-intel, youtube|x, YYYY-MM-DD

## Source
- url: <canonical post url>
- platform: youtube | x
- channel: @handle

## Key findings
- ...

## Swarm fit (tech 1-5)
- ...

## Business angle (1-5)
- ...

## Verdict
keep | archive | follow-up
```

## Guardrails

- Public content only — no paywall bypass, no private DMs.
- Never promote raw scrape (`pending-grok-verification`) to HiveMind without summary + Grok pass.
- **Never write `hivemind-candidate` if any core claim failed Grok (`verdict=false`).**
- Drop items with tech ≤2 AND business ≤2 unless operator explicitly requests archive review.
- Default simulate; no auto-publish of scraped content.
- Budget: max 5 Grok cross-checks per scraped item; defer extras to `needs_human_review`.
