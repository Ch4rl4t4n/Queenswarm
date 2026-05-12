# Queenswarm Changelog

## v1.0.0 (2026-05-12)

### Production release highlights

#### Infrastructure

- Docker Compose deployment (Hetzner VPS target)
- HTTPS via Let's Encrypt (`queenswarm.love`)
- Prometheus + Grafana (`/grafana`, provisioned datasources + dashboards under `docker/grafana/`)
- Celery + Redis task queue
- PostgreSQL + ChromaDB + Neo4j

#### Observability

- Hive Prometheus series: agent gauges, task counters by type/status, task duration histogram, LLM USD counter
- Grafana folder `Queenswarm` with dashboards including “Queenswarm Hive”

#### Notifications

- Optional Slack webhook + SMTP email helpers (`app.core.notifications`)
- `POST /api/v1/system/notify-test` for operator smoke tests
- Dashboard: notifications settings → “Send test notification”

#### API hardening

- Extra Redis sliding windows: `POST .../agents/{id}/run` (default 10/min) and `POST /api/v1/tasks` (default 30/min) per peer IP

#### Security defaults

- Existing JWT + burst/sustain Redis rate limiting retained
- Grafana sub-path hosting with admin password via env

#### LLM routing

- LiteLLM decomposition router with cost ledger entries and Prometheus USD increment per successful hop

---

Prior development history predates this consolidated changelog entry; see git history for step-by-step feature work.
