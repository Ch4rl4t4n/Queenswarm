---
version: 1.0.0
priority: 95
roles: [orchestrator, coder, critic, researcher]
keywords: [maintainer, tech-debt, dependency, upgrade, refactor, coverage, security, cve, pr]
source: queenswarm.love
reference_mode: true
references: docs/harness/QUEEN_MAINTAINER_INSTRUCTIONS.md
---

# Queen Maintainer — Self-Maintaining Codebase Swarm

Purpose: Keep Queenswarm modern, tested, and secure via **PR-only** changes — never direct writes to production branches.

## When to use

- Weekly tech health review (cron routine)
- Manual: „Review tech debt“, „Update dependencies“, „Fix coverage gap“
- After large merge (event trigger — P2)

## Required patterns

- **Planning** + **Prompt Chaining** — tracer bullets before code
- **TDD** — tests first or test update in same PR
- **Reflection** — critic → revise → validate before PR
- **Human-in-the-Loop** — operator merges PR; agent stops at open PR

## Process

1. Read `docs/harness/QUEEN_MAINTAINER_INSTRUCTIONS.md` (behavioral memory)
2. Plan tracer bullets (max 7 steps)
3. Researcher forager: docs, CVEs, deprecation notices
4. Coder sub-swarm: minimal diff, match repo conventions
5. Evaluator + Docker sandbox + pytest/vitest
6. GitHub PR via `github_rest` connector — branch `queen-maintainer/*`
7. Save recipe on verified merge

## Denylist (never modify without explicit operator flag)

- `.env*`, billing, auth, production compose, nginx TLS, secrets

## Output format

1. Tracer bullet plan
2. Research summary with links
3. PR URL + diff summary
4. Test evidence (pass/fail counts)
5. Risks + rollback notes

## Guardrails

- Simulation before any operator-facing report
- CostGovernor budget respected
- Scoped permissions — billing/security paths blocked
