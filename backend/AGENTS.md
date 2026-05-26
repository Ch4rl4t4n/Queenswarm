# Backend — Agent Harness

Python 3.12 · FastAPI · LangGraph · Celery · SQLAlchemy 2.0 async · Pydantic v2 · structlog

## Before editing

1. Read root `AGENTS.md` for philosophy and security
2. Follow `.cursor/rules/queenswarm-python.mdc` for `**/*.py`

## Conventions

- `async def` for all I/O; type hints on every function
- Google-style docstrings; specific exceptions, never bare `except`
- `pathlib.Path`, never `os.path`
- Structured logging: include `agent_id`, `swarm_id`, `task_id` where applicable
- All agents inherit `BaseAgent`; emit pollen after verified task completion
- Workflow steps need explicit `guardrails` dict + `evaluation_criteria`

## Layout

```
backend/app/
  application/services/   # business logic
  domain/                 # entities, enums
  infrastructure/         # ORM, external adapters
  presentation/api/       # FastAPI routers
  worker/                 # Celery tasks
  skills/                 # markdown agent skills
```

## API

- Routers under `presentation/api/routers/`, mounted in `v1.py`
- Auth: `require_dashboard_user_with_tenant_role` (JWT)
- Platform features: `resolve_platform_features_for_subscription`

## Testing

```bash
cd backend && pytest tests/test_<module>_unit.py -q
```

Mock LLM, scraping, Slack. Target 80% coverage. pytest-asyncio for async tests.

## Migrations

Alembic versions in `backend/alembic/versions/`. Run before prod deploy.

## Feature flags (env)

Examples: `DUMP_SLEEP_ENABLED`, `QUEEN_MAINTAINER_ENABLED`, `SUPERVISOR_PATTERN_ROUTER_ENABLED`, `OPERATOR_CONTROL_PLANE_ENABLED`, `HIVE_INNOVATION_LAB_ENABLED` — see `app/core/config.py`.

Operator Control Plane compose services live in `application/services/operator_control_plane.py` plus module files (`context_teleport.py`, `regret_simulator.py`, `swarm_immune_system.py`, etc.). Gate: `./scripts/audit-operator-control-plane-gate.sh`.

## Curated memory kinds

`mission`, `ideal_state`, `soul`, `skills_hierarchy`, `instructions` — rendered via `CuratedMemoryService.render_prompt_prefix()`.
