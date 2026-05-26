# Queenswarm — Agent Harness (root)

Layered harness for coding agents. **Harness > model.** Read scoped docs before editing.

## Scope map

| Path | Doc | When to read |
|------|-----|--------------|
| Repo root | `AGENTS.md` (this file) | Always — philosophy, security, deploy |
| `backend/` | `backend/AGENTS.md` | Python, API, Celery, agents, DB |
| `frontend/` | `frontend/AGENTS.md` | Next.js, UI, responsive shell |

Also: `.cursorrules`, `.cursor/rules/*.mdc` — IDE-specific rules.

## Bee-hive philosophy (non-negotiable)

- One agent = one bee, one sharp job
- Decompose tasks into 3–7 atomic sub-workflows
- Decentralized sub-swarms (5–10 bees), global sync ~5 min
- Pollen rewards for **verified** outcomes only
- Recipe Library saves every verified workflow
- Rapid Learning Loop target: under 60s when feasible
- **Never** report raw LLM output without simulation/verification

## Security

- All secrets via env vars (Pydantic Settings) — never literals
- JWT on all endpoints except `/health`, `/metrics`, `/docs`
- Docker sandbox for code execution: network none, 256MB, 0.5 CPU, 30s
- Rate limit: Redis sliding window

## Deploy

```bash
./scripts/deploy-prod.sh   # always --env-file .env.prod
```

Migrations before traffic switch. Health check must pass.

## Behavioral memory (tenant)

Operators edit tenant `instructions` curated memory in **Settings → AI · harness** or **Knowledge → Curated memory**. Injected as `=== BEHAVIORAL INSTRUCTIONS ===` in Queen prompts.

## Queen Maintainer

PR-only self-maintenance. Never direct write to `main`. Denylist: `.env*`, billing, prod compose. See `docs/harness/QUEEN_MAINTAINER_INSTRUCTIONS.md`.

## Key docs

- `docs/ROADMAP.md` — phased product plan
- `docs/FEATURE_IMPLEMENTATION_GUARDRAILS.md` — mandatory perf + safety checklist for new features
- `docs/QUEENSWARM_DESIGN_PATTERNS.md` — agentic patterns (Kashef)
- `docs/HARNESS_SELF_MAINTAINING_ANALYSIS.md` — harness video synthesis
