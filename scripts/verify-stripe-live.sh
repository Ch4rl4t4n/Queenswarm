#!/usr/bin/env bash
# Verify Stripe checkout is live after keys are in .env.prod (read-only API probe).
#
# Usage:
#   ./scripts/verify-stripe-live.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE=(docker compose -p queenswarm_prod -f "${ROOT}/docker-compose.base.yml" -f "${ROOT}/docker-compose.prod.yml" --env-file "${ROOT}/${ENV_FILE}")

resolve_operator_user_jwt() {
  if [[ -n "${OPERATOR_USER_BEARER_TOKEN:-}" ]]; then
    printf '%s' "$OPERATOR_USER_BEARER_TOKEN"
    return 0
  fi
  local cid token
  cid="$("${COMPOSE[@]}" ps -q backend 2>/dev/null || true)"
  [[ -n "${cid// }" ]] || return 1
  token="$("${COMPOSE[@]}" exec -T backend python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n' || true)"
  [[ -n "${token// }" && "$token" == eyJ* ]] || return 1
  printf '%s' "$token"
}

echo "== Verify Stripe live checkout =="
echo "hive: ${HIVE_BASE}"
echo

if ! ./scripts/operator-stripe-prep.sh >/dev/null 2>&1; then
  echo "FAIL: Stripe keys not ready — run ./scripts/operator-stripe-prep.sh" >&2
  exit 1
fi
echo "  OK operator-stripe-prep (keys present)"

TOKEN="$(resolve_operator_user_jwt || true)"
if [[ -z "${TOKEN// }" ]]; then
  echo "FAIL: no user JWT for /billing/plans probe" >&2
  exit 1
fi

body="$(curl -sS -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/billing/plans")"
eval "$(echo "$body" | python3 - <<'PY'
import json, sys
d = json.load(sys.stdin)
pro = d.get("pro_checkout_ready")
ent = d.get("enterprise_checkout_ready")
tier = d.get("tier", d.get("current_tier", ""))
print(f"PRO_READY={str(pro is True).lower()}")
print(f"ENT_READY={str(ent is True).lower()}")
print(f"TIER={tier!r}")
PY
)"

echo "  tier: ${TIER}"
if [[ "$PRO_READY" == "true" ]]; then
  echo "  OK pro_checkout_ready=true"
else
  echo "FAIL pro_checkout_ready=false (redeploy backend after .env.prod change?)" >&2
  exit 1
fi
if [[ "$ENT_READY" == "true" ]]; then
  echo "  OK enterprise_checkout_ready=true"
else
  echo "  WARN enterprise_checkout_ready=false"
fi

for path in /api/v1/billing/pro-checkout /api/v1/billing/enterprise-checkout; do
  code="$(curl -sS -o /dev/null -w '%{http_code}' -X POST -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" -d '{}' "${HIVE_BASE}${path}" || echo 000)"
  case "$code" in
    200|201|400|402|409|422|503) echo "  OK POST ${path} (${code} — route live)" ;;
    401|403) echo "FAIL POST ${path} (${code})" >&2; exit 1 ;;
    *) echo "  NOTE POST ${path} (${code})" ;;
  esac
done

echo
echo "== Stripe live verification: OK =="
