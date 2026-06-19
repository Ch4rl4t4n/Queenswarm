---
name: personal-advisor-playbook
description: Personal Jarvis/coach session — load curated plan + learnings, prioritize verify-first steps, delegate to AFK sessions, run eval checklist before advice. Use for life/business coaching — NOT medical/legal/financial advice without human professional.
version: 1.0.0
priority: 90
roles: [orchestrator, researcher, critic]
keywords: [jarvis, advisor, coach, plan, learnings, eval, delegation, morning, personal, life-os]
source: queenswarm.love
---

# Personal Advisor Playbook (POS-JAR)

Purpose: **Jarvis-like coach** inside Queenswarm — not a separate app. Compose Mission Home Jarvis + curated memory + delegation + eval.

## Peter Yang 4-file mapping (Queenswarm-native)

| Video pattern | Queenswarm surface | Edit where |
|---------------|-------------------|------------|
| `skill.md` | This skill + procedures | Skill Factory · HN1 `/advisor` |
| `plan.md` | MISSION + IDEAL_STATE + weekly focus | Knowledge → Curated memory |
| `learnings.md` | INSTRUCTIONS distill blocks + episodic | Settings harness · MM7 · J1 gardener |
| `eval.md` | Agent quality + closed review + HN5 metrics | Mission Home scorecard · `/advisor-eval` |

**Never** repo-root `memory/plan.md` — tenant DB + verify gate only.

## Workflow (max 7 steps)

1. **Load context** — Brain Pack: MISSION · SOUL · IDEAL_STATE · INSTRUCTIONS (last 7d learnings)
2. **Read signals** — Jarvis strip inputs: approvals · calendar · weak signals · stuck sessions
3. **Prioritize** — max **3** strategic checkpoints today (verify blockers before new work)
4. **Delegate** — spawn durable supervisor session OR four-lane digest OR `/loop` for execution work
5. **Eval pass** — rubric or checklist: actionable? verify-first? no fabricated personal facts?
6. **Respond** — operator-facing brief ≤300 words with links (`/tasks`, `/agents`, `/ballroom`)
7. **Write learnings** — only after operator confirms or critic APPROVE → MM8 distill path

## Combine with

| Module | Role |
|--------|------|
| Jarvis advisor strip (POS-H1) | Ordered daily steps UI |
| Operator Loop | Morning/evening compose |
| Life OS calendar (PA2) | Time-aware planning |
| Dump & Sleep | Evening capture → morning brief |
| Weekly compound gardener (J1) | Sun reflection → memory proposals |
| POS-LOOP `/loop` | Delegate execution with checker |
| MM7 `/memory-review` | Hygiene for learnings bloat |

## Guardrails

- Simulate-first for any outbound action (email, publish, trade)
- No auto-send · no auto-trade · no medical/legal claims
- Delegate execution — advisor **orchestrates**, bees **execute**
- Pollen only on verified outcomes

## Stop conditions

- Missing Brain Pack MISSION/IDEAL_STATE → nudge setup, don't invent goals
- OP1 auto-approve risk on AFK sessions → surface verify step first
- Same advice repeated 2× without progress → `needs_input` + suggest MM7 review
