# Phase 6.2 - Supervisor Observability Strip

## Scope

This phase adds lightweight runtime observability for supervisor operations without changing existing workflows.

- Additive API: `GET /api/v1/agents/sessions/summary`
- Additive FE telemetry cards on `/agents`
- Additive Prometheus lifecycle counters for sessions/routines

## Backend

### New summary endpoint

Implemented in `backend/app/presentation/api/routers/agent_sessions.py`:

- Computes aggregate session counts grouped by status
- Computes routine totals, active routines, and currently due routines
- Returns a compact response for dashboard polling

Response shape:

- `sessions_total`
- `status_counts`
- `running_sessions`
- `needs_input_sessions`
- `completed_sessions`
- `routines_total`
- `active_routines`
- `due_routines`

### Prometheus counters

Implemented in `backend/app/core/metrics.py`:

- `queenswarm_supervisor_sessions_total{event,runtime_mode}`
- `queenswarm_supervisor_routines_total{event}`

Wired into session/routine lifecycle in:

- `backend/app/application/services/supervisor/session_service.py`
- `backend/app/application/services/supervisor/routine_service.py`

## Frontend

Updated `frontend/components/hive/agents-sessions-panel.tsx`:

- Polls `agents/sessions/summary`
- Renders compact cards for key control-plane telemetry:
  - Sessions total
  - Running / needs input
  - Routines total
  - Active / due

## Tests

- Added API unit test for summary endpoint:
  - `backend/tests/test_agent_sessions_api_unit.py`
- Added OpenAPI path regression assertion:
  - `backend/tests/connectors/test_openapi_phase0_paths.py`

## Compatibility

- No breaking API changes
- Existing session/routine endpoints unchanged
- Feature works with existing Phase 6.1 flags and data model
