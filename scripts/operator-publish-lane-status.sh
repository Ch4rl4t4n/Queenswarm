#!/usr/bin/env bash
# Unified publish lane readiness — JSON summary for operator hub / handoff.
#
# Usage:
#   ./scripts/operator-publish-lane-status.sh
#   ./scripts/operator-publish-lane-status.sh --json-only
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

JSON_ONLY="${1:-}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

if ! docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  echo '{"error":"backend_not_running"}' >&2
  exit 1
fi

TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null || true)"
if [[ -z "${TOKEN// }" ]]; then
  echo '{"error":"jwt_mint_failed"}' >&2
  exit 1
fi

hub_json="$(curl -sS -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/settings/operator-hub" 2>/dev/null || echo '{}')"
simulate_ok="unknown"
if ./scripts/operator-publish-simulate-gate.sh >/dev/null 2>&1; then
  simulate_ok="pass"
else
  simulate_ok="fail"
fi

export hub_json simulate_ok HIVE_BASE
python3 <<'PY'
import json
import os

hub = json.loads(os.environ.get("hub_json") or "{}")
po = hub.get("publish_onboarding") or {}
so = hub.get("social_oauth") or {}
na = hub.get("next_action") or {}

out = {
    "hive_base": os.environ.get("HIVE_BASE"),
    "publish_onboarding_pct": po.get("progress_pct"),
    "oauth_env_configured": so.get("env_configured_count"),
    "oauth_active_channels": so.get("active_channel_count"),
    "ready_publish_items": so.get("ready_items_count"),
    "live_publish_enabled": so.get("live_publish_enabled"),
    "simulate_gate": os.environ.get("simulate_ok"),
    "next_action_title": na.get("title"),
    "next_action_step_id": na.get("step_id"),
    "blockers": so.get("blockers") or [],
}
print(json.dumps(out, indent=2))
PY

if [[ "$JSON_ONLY" == "--json-only" ]]; then
  exit 0
fi

echo
echo "Docs: docs/OPERATOR_FIRST_LIVE_POST.md"
echo "Prep: ./scripts/operator-social-oauth-prep-all.sh"
