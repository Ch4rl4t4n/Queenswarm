# Queenswarm Changelog

## Phase R — 2026-05-13 (pre-v1.0.0 ship hardening)

- Dynamic agent swarm (29 bees / 4 swarms) cockpit refinements  
- Hex agent cards: pointy-top **SVG stroke** borders (~3px), amber `#FFB800` when undifferentiated swarm color, swarm hue when anchored (`swarm_id` / `sub_swarm_id`), running glow via `drop-shadow`
- Agents roster filter: **Nezaradení** keyed off **`sub_swarm_id` absent**; lane tabs count only bees with real sub-swarm placement + semantic hints
- LLM router: mapper configure fix (`Task` registered before vault refresh); Grok-first → Claude Haiku fallback in prod smoke
- Workflows page: client **DAG** board (`/workflows`), 8s refresh, expand-to-fetch steps, progress bar, pause/cancel via operator proxy
- Ballroom: WebSocket voice + text session cockpit (prior releases)
- Agent detail: config, task history, run/pause (prior)
- Task result drawer: polling / re-run (prior)
- Mobile-responsive cockpit shell

Git: release pointer tag `v1.0.0-phase-r` marks this drop (tag `v1.0.0` may already exist on an earlier commit).

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
