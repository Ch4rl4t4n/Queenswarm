# Phase 6.3 - Supervisor Grafana Telemetry

## Goal

Expose the Phase 6.2 supervisor observability metrics directly in Grafana for operators.

## Delivered

- Extended dashboard: `docker/grafana/dashboards/queenswarm.json`
- Added Supervisor Control Plane panels:
  - Supervisor Sessions Created
  - Supervisor Sessions Queued (durable)
  - Routines Triggered
  - Routines Failed
  - Supervisor Event Rate (per minute, 5m rate)

## Metric sources

- `queenswarm_supervisor_sessions_total{event,runtime_mode}`
- `queenswarm_supervisor_routines_total{event}`

Both are emitted from supervisor session/routine lifecycle services and scraped by Prometheus as part of existing stack.

## Verification

- Unit tests extended in `backend/tests/test_observability_metrics.py` for both new counters and label dimensions.
- Dashboard stays under existing provisioning path (`/var/lib/grafana/dashboards`) and requires no provisioning changes.

## Compatibility

- Additive dashboard-only enhancement
- No API contract changes
- No migration required
