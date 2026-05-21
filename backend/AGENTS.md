# Queenswarm — Backend agent harness

Parent: [`../AGENTS.md`](../AGENTS.md)

## Stack

Python 3.12 · FastAPI · LangGraph · Celery · SQLAlchemy 2.0 async · Pydantic v2 · structlog

## Rules

- `async def` for all I/O; type hints on every public function
- Google-style docstrings; specific exceptions only
- `pathlib.Path`, f-strings, Pydantic Settings for config
- Structured logs: include `agent_id`, `swarm_id`, `task_id` when applicable
- Agents inherit `BaseAgent`; award pollen after verified task completion
- Workflow steps: explicit `guardrails` + `evaluation_criteria`

## Key modules

| Concern | Location |
|---------|----------|
| Supervisor / patterns | `app/application/services/supervisor/` |
| Harness snapshot | `app/application/services/harness_snapshot.py` |
| Tool marketplace | `app/application/services/tool_marketplace.py` |
| Queen Maintainer | `app/presentation/api/routers/queen_maintainer.py` |
| Tests | `tests/` (pytest-asyncio) |

## Testing

```bash
cd backend && ./venv/bin/pytest -q --no-cov
```

Coverage gate: 80% in CI (`backend/.coveragerc`).
