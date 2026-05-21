# Queenswarm — Agent harness (root)

This file is the **root layer** of the layered harness. Agents and coding tools should read it before module-specific rules.

## Layer order (harness > model)

1. `AGENTS.md` (this file) — product philosophy and repo map
2. `backend/AGENTS.md` — Python / FastAPI / LangGraph conventions
3. `frontend/AGENTS.md` — Next.js 15 App Router conventions
4. `.cursorrules` — full bee-hive rules for Cursor
5. `.cursor/rules/*.mdc` — scoped editor rules

## Philosophy (non-negotiable)

- One agent = one bee — single sharp responsibility
- Decompose work into 3–7 atomic steps; verify before user-facing output
- Decentralized sub-swarms; global hive sync ~5 minutes
- Pollen rewards + Recipe Library for verified workflows
- Never hardcode secrets; never skip simulation for operator-facing results

## Repo map

| Area | Path |
|------|------|
| API | `backend/app/presentation/api/` |
| Agents / supervisor | `backend/app/application/services/supervisor/` |
| Skills | `backend/app/skills/` |
| Dashboard UI | `frontend/app/(dashboard)/` |
| Harness settings | `/settings/harness` |
| Capabilities atlas | `/settings/capabilities` |

## Operator docs

- Roadmap: `docs/ROADMAP.md`
- Mission backlog: `docs/MISSION_EXECUTION_BACKLOG.md`
- Harness analysis: `docs/HARNESS_SELF_MAINTAINING_ANALYSIS.md`
- Behavioral memory: `docs/harness/QUEEN_MAINTAINER_INSTRUCTIONS.md` (tenant copy via Settings)

## Maintainer safety

Queen Maintainer and harness automation are **PR-only** on branches `queen-maintainer/*` — never commit directly to `main`.
