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

## CI parity (avoid red emails)

Before pushing to `main`, run the same gates GitHub Actions runs:

```bash
./scripts/ci-local.sh all              # backend (80% cov via .coveragerc) + frontend e2e subset + security
./scripts/ci-local.sh --whole-app      # release gate (critical journeys + a11y)
```

**Common drift traps:**

- `scripts/ci-local.sh` must not override `--cov-fail-under` — use `backend/.coveragerc` only (80%).
- E2E stubs: do not set `skill_factory: true` globally in `shell-api-mocks.ts` — it hides Integrations **Skills export** tab.
- IA: new Apps & Tools routes belong in `buildCanonicalNavGroups` Apps & Tools group, not `CANONICAL_MORE_ONLY_HREFS`.
- E2E selectors: prefer `getByRole("heading", { name })` when subnav duplicates labels.

## Behavioral memory (tenant)

Operators edit tenant `instructions` curated memory in **Settings → AI · harness** or **Knowledge → Curated memory**. Injected as `=== BEHAVIORAL INSTRUCTIONS ===` in Queen prompts.

## Queen Maintainer

PR-only self-maintenance. Never direct write to `main`. Denylist: `.env*`, billing, prod compose. See `docs/harness/QUEEN_MAINTAINER_INSTRUCTIONS.md`.

## Key docs

- `docs/ROADMAP.md` — phased product plan
- `docs/FEATURE_IMPLEMENTATION_GUARDRAILS.md` — mandatory perf + safety checklist for new features
- `docs/QUEENSWARM_DESIGN_PATTERNS.md` — agentic patterns (Kashef)
- `docs/HARNESS_SELF_MAINTAINING_ANALYSIS.md` — harness video synthesis
