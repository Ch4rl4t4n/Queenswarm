---
version: 1.0.0
priority: 88
roles: critic, designer, coder
keywords: rubric, closed-loop, self-heal, review, greptile, score
---
# Closed Review Loop (LOOP1)

Run a **scored closed loop** before operator approve or publish simulate.

## Workflow

1. **Evaluate** — score draft against a rubric template (`marketing-creative`, `code-review`, etc.)
2. **Compare** — pass when `confidence >= min_score` AND `is_valid` (respect LOOP2 guardrails)
3. **Self-heal** — if fail and turns remain, revise draft from critic feedback (no new facts)
4. **Re-run** — evaluate revised draft until pass or `max_turns`

## Guardrails

- Default max turns + min score from **Settings → Loop guardrails** (LOOP2)
- Never skip simulate-first for live publish
- Store last rubric score on session context as `loop_last_rubric_score` when dispatched from supervisor

## When to use

- Marketing copy before publish queue (**NP6** campaign wizard)
- Harness / Maintainer PR slices before merge
- Any subjective output needing ≥4/5 rubric gate
