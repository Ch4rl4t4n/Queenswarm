# Phase 6.1 Lightweight Upgrade Report

Date: 2026-05-15

## Scope

Phase 6.1 adds four additive capabilities on top of Phase 6.0:

1. Lightweight Markdown skills system
2. Retrieval contract for shared context
3. Light control-plane review actions
4. Recurring/scheduled routines using Celery

All changes are backward compatible and feature-flagged.

## Delivered Components

### 1) Lightweight Skills System

- Added Markdown skill assets under `backend/app/skills/`:
  - `grill-me.md`
  - `context.md`
  - `decide.md`
  - `tdd.md`
  - `diagnose.md`
- Added `SkillLibrary` loader in `backend/app/application/services/supervisor/skills.py`.
- Supervisor/sub-agent runtime now resolves role-aligned skill slugs and injects compact prompt blocks on-demand.

### 2) Retrieval Contract

- Expanded `SharedContextService` with:
  - contract parsing
  - retrieval bundle resolution
  - compact prompt rendering
- Supported contract sections:
  - `customer_history`
  - `policy`
  - `last_3_tasks`
  - `recent_events`
  - `semantic_memory`
  - `graph_context`
- Retrieval uses existing `pgvector` + Neo4j integrations (`semantic_search`, `find_related`).

### 3) Light Control Plane

- Added approval/reject flow for sessions:
  - `POST /api/v1/agents/sessions/{session_id}/review`
- Added `needs_input` lifecycle action to session controls.
- Frontend dashboard now exposes approve/reject controls in the sessions panel and detail drawer.

### 4) Routines + Scheduled Tasks

- Added routine model and migration:
  - `supervisor_routines` table (`0018_supervisor_routines`)
- Added routine service APIs:
  - `POST /api/v1/agents/routines`
  - `GET /api/v1/agents/routines`
  - `POST /api/v1/agents/routines/{routine_id}/trigger`
- Added Celery tick task:
  - `hive.supervisor_routines_tick`
- Added beat schedule wiring when `ROUTINES_ENABLED=true`.

## Feature Flags

- `SUPERVISOR_SKILLS_ENABLED`
- `RETRIEVAL_CONTRACT_ENABLED`
- `LIGHT_CONTROL_PLANE_ENABLED`
- `ROUTINES_ENABLED`

Defaults are safe in config (`false`), with explicit opt-in in environment files.

## Backward Compatibility

- Existing `/agents/sessions*` flows remain additive and compatible.
- Existing supervisor session schema unchanged; routines are a new table.
- Existing task/scheduler/Celery routes continue to run unchanged.
- Existing dashboard auth/proxy behavior preserved.

## Verification Plan

- Backend unit + API tests for:
  - skills loader
  - retrieval parser
  - review endpoint
  - routines endpoint behavior
- OpenAPI regression for new paths
- Frontend unit test update for session status helper
- Frontend lint/type/build check
