#!/usr/bin/env bash
# Emergency: stop Grok-burning workloads and switch tenant to free-first routing.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE=(docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml --env-file "$ENV_FILE")

echo "==> Stopping supervisor sessions + disabling auto-approve (prod DB)"
"${COMPOSE[@]}" exec -T postgres psql -U queenswarm -d queenswarm <<'SQL'
BEGIN;

-- Kill Grok vault credential (key also lived here when GROK_API_KEY env empty).
DELETE FROM hive_llm_secrets WHERE provider = 'grok';

-- Stop burn loops immediately.
UPDATE sub_agent_sessions
SET status = 'stopped', error_text = 'operator_emergency_grok_disconnect'
WHERE status IN ('running', 'queued', 'pending', 'needs_input');

UPDATE supervisor_sessions
SET status = 'stopped'
WHERE status IN ('running', 'needs_input', 'paused');

UPDATE supervisor_routines SET is_active = false WHERE is_active = true;

UPDATE agent_configs SET is_active = false WHERE is_active = true;

-- Tenant policy: no auto-approve loops; free-first only, no paid upgrade hops.
UPDATE tenants
SET operator_settings = jsonb_set(
  jsonb_set(
    jsonb_set(
      COALESCE(operator_settings, '{}'::jsonb),
      '{supervisor_sessions}',
      COALESCE(operator_settings->'supervisor_sessions', '{}'::jsonb) || '{"auto_approve_enabled": false, "auto_approve_enabled_source": "tenant"}'::jsonb,
      true
    ),
    '{llm_routing}',
    '{"routing_mode": "free_first", "cost_guardian_enabled": true, "auto_upgrade_on_failure": false}'::jsonb,
    true
  ),
  '{skill_factory}',
  COALESCE(operator_settings->'skill_factory', '{}'::jsonb) || '{"auto_build_enabled": false, "research_cron_enabled": false}'::jsonb,
  true
);

COMMIT;

SELECT 'running_sessions' AS metric, COUNT(*)::text AS value FROM supervisor_sessions WHERE status = 'running'
UNION ALL
SELECT 'grok_vault_rows', COUNT(*)::text FROM hive_llm_secrets WHERE provider = 'grok'
UNION ALL
SELECT 'active_routines', COUNT(*)::text FROM supervisor_routines WHERE is_active;
SQL

echo "==> Purging Celery hive queue (pending supervisor / grok tasks)"
REDIS_PASS="$(grep -E '^REDIS_PASSWORD=' "$ENV_FILE" | cut -d= -f2- || true)"
if [[ -n "${REDIS_PASS}" ]]; then
  "${COMPOSE[@]}" exec -T redis redis-cli -a "$REDIS_PASS" --no-auth-warning DEL celery 2>/dev/null || true
  "${COMPOSE[@]}" exec -T redis redis-cli -a "$REDIS_PASS" --no-auth-warning KEYS 'celery-task-meta-*' 2>/dev/null | head -c 20000 | \
    xargs -r -I{} "${COMPOSE[@]}" exec -T redis redis-cli -a "$REDIS_PASS" --no-auth-warning DEL {} 2>/dev/null || true
fi

echo "==> Done. Restart backend + celery workers to pick up .env.prod Grok-off flags."
