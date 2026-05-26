#!/usr/bin/env bash
# Authenticated prod walkthrough gate — automated slice + manual checklist pointer.
#
# Unauthenticated: verifies supervisor/playbook routes exist on prod (401/403, never 404).
# Local E2E: phase61 supervisor + phase14 playbook flows (mocked API — CI parity).
# Optional authenticated smoke when OPERATOR_BEARER_TOKEN is set (read-only GETs).
#
# Usage:
#   ./scripts/prod-walkthrough-gate.sh
#   PLAYWRIGHT_BASE_URL=https://queenswarm.love ./scripts/prod-walkthrough-gate.sh
#   OPERATOR_BEARER_TOKEN=eyJ... ./scripts/prod-walkthrough-gate.sh
#
# Env:
#   HIVE_BASE               — prod hive for curl probes (default https://queenswarm.love)
#   OPERATOR_BEARER_TOKEN   — optional dashboard:proxy JWT (issue_dashboard_jwt.py) for cockpit smoke
#   AUTO_DASHBOARD_JWT=0    — skip auto dashboard:proxy JWT from prod backend container
#   AUTO_OPERATOR_USER_JWT=0 — skip auto user JWT from prod backend container
#   OPERATOR_USER_BEARER_TOKEN — optional full user JWT for session/enterprise routes
#   SKIP_E2E=1              — skip Playwright suites
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-${PLAYWRIGHT_BASE_URL:-https://queenswarm.love}}"
SKIP_E2E="${SKIP_E2E:-0}"
ENV_FILE="${ENV_FILE:-.env.prod}"
FAKE_SESSION_ID="00000000-0000-4000-8000-000000000001"
COMPOSE=(docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml --env-file "$ENV_FILE")

resolve_dashboard_jwt() {
  if [[ -n "${OPERATOR_BEARER_TOKEN:-}" ]]; then
    printf '%s' "$OPERATOR_BEARER_TOKEN"
    return 0
  fi
  if [[ "${AUTO_DASHBOARD_JWT:-1}" != "1" ]]; then
    return 1
  fi
  if ! command -v docker >/dev/null 2>&1; then
    return 1
  fi
  local cid token
  cid="$("${COMPOSE[@]}" ps -q backend 2>/dev/null || true)"
  if [[ -z "${cid// }" ]]; then
    return 1
  fi
  token="$("${COMPOSE[@]}" exec -T backend python scripts/issue_dashboard_jwt.py 2>/dev/null | tr -d '\r\n' || true)"
  if [[ -n "${token// }" && "$token" == eyJ* ]]; then
    printf '%s' "$token"
    return 0
  fi
  return 1
}

resolve_operator_user_jwt() {
  if [[ -n "${OPERATOR_USER_BEARER_TOKEN:-}" ]]; then
    printf '%s' "$OPERATOR_USER_BEARER_TOKEN"
    return 0
  fi
  if [[ "${AUTO_OPERATOR_USER_JWT:-1}" != "1" ]]; then
    return 1
  fi
  if ! command -v docker >/dev/null 2>&1; then
    return 1
  fi
  local cid token
  cid="$("${COMPOSE[@]}" ps -q backend 2>/dev/null || true)"
  if [[ -z "${cid// }" ]]; then
    return 1
  fi
  token="$("${COMPOSE[@]}" exec -T backend python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n' || true)"
  if [[ -n "${token// }" && "$token" == eyJ* ]]; then
    printf '%s' "$token"
    return 0
  fi
  return 1
}

solo_mode_enabled() {
  [[ -f "$ENV_FILE" ]] || return 1
  local val
  val="$(grep -E '^SOLO_MODE_ENABLED=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '\r"'"'"' ' || true)"
  [[ "${val,,}" == "true" || "$val" == "1" ]]
}

echo "== Queenswarm prod walkthrough gate =="
echo "hive: ${HIVE_BASE}"
echo

expect_auth_route() {
  local path="$1"
  local label="${2:-$path}"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' "${HIVE_BASE}${path}" || echo "000")"
  if [[ "$code" == "404" || "$code" == "000" ]]; then
    echo "FAIL ${label} HTTP ${code} (expected auth gate, not missing route)" >&2
    exit 1
  fi
  echo "  OK ${label} (${code} — route wired)"
}

echo "[1/5] supervisor + playbook API routes (unauthenticated)"
for path in \
  /api/v1/agents/sessions \
  /api/v1/agents/sessions/summary \
  "/api/v1/agents/sessions/${FAKE_SESSION_ID}/playbook/preview" \
  "/api/v1/agents/sessions/${FAKE_SESSION_ID}/playbook" \
  /api/v1/settings/team/session-playbook/config \
  /api/v1/billing/plans \
  /api/v1/dashboard/rapid-loop \
  /api/v1/dashboard/time-saved \
  /api/v1/dashboard/cockpit \
  /api/v1/settings/enterprise/config \
  /api/v1/learning/bee-badges/catalog \
  /api/v1/marketing/lead-magnets; do
  expect_auth_route "$path"
done

echo
echo "[2/5] protected hub shells (redirect or auth, not 404)"
for path in /agents /integrations /tasks /knowledge /ballroom /swarms/new /settings/billing /settings/capabilities /settings/enterprise; do
  code="$(curl -sS -o /dev/null -w '%{http_code}' "${HIVE_BASE}${path}" || echo "000")"
  if [[ "$code" == "404" || "$code" == "000" ]]; then
    echo "FAIL ${path} HTTP ${code}" >&2
    exit 1
  fi
  echo "  OK ${path} (${code})"
done

if resolved_jwt="$(resolve_dashboard_jwt)"; then
  echo
  if [[ -n "${OPERATOR_BEARER_TOKEN:-}" ]]; then
    echo "[3/5] authenticated dashboard smoke (OPERATOR_BEARER_TOKEN / dashboard:proxy)"
  else
    echo "[3/5] authenticated dashboard smoke (auto dashboard:proxy JWT from prod backend)"
  fi
  auth_header="Authorization: Bearer ${resolved_jwt}"
  for path in \
    /api/v1/dashboard/cockpit \
    /api/v1/dashboard/time-saved \
    /api/v1/learning/bee-badges/catalog; do
    code="$(curl -sS -o /dev/null -w '%{http_code}' -H "$auth_header" "${HIVE_BASE}${path}" || echo "000")"
    if [[ "$path" == "/api/v1/learning/bee-badges/catalog" ]] && solo_mode_enabled && [[ "$code" == "403" ]]; then
      echo "  OK ${path} (403 — bee_gamification hidden in solo mode)"
      continue
    fi
    if [[ "$code" != "200" ]]; then
      echo "FAIL ${path} HTTP ${code} (expected 200 with dashboard:proxy JWT)" >&2
      exit 1
    fi
    echo "  OK ${path} (200)"
  done
else
  echo
  echo "[3/5] authenticated dashboard smoke — skipped (set OPERATOR_BEARER_TOKEN or run prod backend for auto JWT)"
fi

if resolved_user_jwt="$(resolve_operator_user_jwt)"; then
  echo
  if [[ -n "${OPERATOR_USER_BEARER_TOKEN:-}" ]]; then
    echo "[3b/5] authenticated user smoke (OPERATOR_USER_BEARER_TOKEN)"
  else
    echo "[3b/5] authenticated user smoke (auto user JWT from prod backend)"
  fi
  user_header="Authorization: Bearer ${resolved_user_jwt}"
  for path in \
    /api/v1/agents/sessions/summary \
    "/api/v1/agents/sessions?limit=5" \
    /api/v1/settings/enterprise/config \
    /api/v1/billing/plans \
    /api/v1/dashboard/rapid-loop; do
    code="$(curl -sS -o /dev/null -w '%{http_code}' -H "$user_header" "${HIVE_BASE}${path}" || echo "000")"
    if solo_mode_enabled; then
      case "$path" in
        /api/v1/settings/enterprise/config)
          if [[ "$code" == "403" ]]; then
            echo "  OK ${path} (403 — enterprise hidden in solo mode)"
            continue
          fi
          ;;
        /api/v1/billing/plans)
          if [[ "$code" == "403" || "$code" == "404" ]]; then
            echo "  OK ${path} (${code} — billing hidden in solo mode)"
            continue
          fi
          ;;
      esac
    fi
    if [[ "$code" != "200" ]]; then
      echo "FAIL ${path} HTTP ${code} (expected 200 with user JWT)" >&2
      exit 1
    fi
    echo "  OK ${path} (200)"
  done
else
  echo
  echo "[3b/5] authenticated user smoke — skipped (set OPERATOR_USER_BEARER_TOKEN or run prod backend for auto JWT)"
fi

echo
if solo_mode_enabled; then
  echo "[4/5] public lead magnet landings — skipped (solo mode: ugc_content_engine hidden)"
  echo "[4c/5] public lead magnet API — skipped (solo mode)"
  echo "[4d/5] billing + enterprise HA evidence — skipped (solo mode)"
else
  echo "[4/5] public lead magnet landings"
  for magnet in exec-assistant lead-waterfall content-flywheel; do
    magnet_code="$(curl -sS -o /dev/null -w '%{http_code}' "${HIVE_BASE}/magnet/${magnet}" || echo "000")"
    if [[ "$magnet_code" == "200" ]]; then
      echo "  OK /magnet/${magnet} (${magnet_code})"
    else
      echo "FAIL /magnet/${magnet} HTTP ${magnet_code}" >&2
      exit 1
    fi
  done

  echo
  echo "[4c/5] public lead magnet API payloads"
  for magnet in exec-assistant lead-waterfall content-flywheel; do
    code="$(curl -sS -o /dev/null -w '%{http_code}' "${HIVE_BASE}/api/v1/marketing/lead-magnets/${magnet}" || echo "000")"
    if [[ "$code" == "200" ]]; then
      echo "  OK GET /api/v1/marketing/lead-magnets/${magnet} (${code})"
    else
      echo "FAIL lead-magnet API ${magnet} HTTP ${code}" >&2
      exit 1
    fi
  done

  if resolved_user_jwt="$(resolve_operator_user_jwt 2>/dev/null || true)" && [[ -n "${resolved_user_jwt:-}" ]]; then
    echo
    echo "[4d/5] billing plans + enterprise HA evidence (user JWT)"
    user_header="Authorization: Bearer ${resolved_user_jwt}"
    plans_body="$(curl -sS -H "$user_header" "${HIVE_BASE}/api/v1/billing/plans" || echo "{}")"
    if echo "$plans_body" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if any(k in d for k in ('tier','plans','pro_checkout_ready')) else 1)" 2>/dev/null; then
      echo "  OK /api/v1/billing/plans payload"
    else
      echo "FAIL /api/v1/billing/plans unexpected payload" >&2
      exit 1
    fi
    ent_body="$(curl -sS -H "$user_header" "${HIVE_BASE}/api/v1/settings/enterprise/config" || echo "{}")"
    if echo "$ent_body" | python3 -c "import json,sys; d=json.load(sys.stdin); hp=d.get('ha_profile') or {}; sys.exit(0 if hp.get('dr_drill') is not None and hp.get('ha_chaos') is not None else 1)" 2>/dev/null; then
      echo "  OK enterprise ha_profile includes dr_drill + ha_chaos"
    else
      echo "FAIL enterprise ha_profile missing drill/chaos evidence" >&2
      exit 1
    fi
  fi
fi

echo
echo "[4b/5] billing checkout routes (POST — expect 401 without JWT)"
for path in /api/v1/billing/pro-checkout /api/v1/billing/enterprise-checkout; do
  code="$(curl -sS -o /dev/null -w '%{http_code}' -X POST "${HIVE_BASE}${path}" || echo "000")"
  if [[ "$code" == "401" || "$code" == "403" ]]; then
    echo "  OK POST ${path} (${code})"
  else
    echo "FAIL POST ${path} HTTP ${code} (expected 401)" >&2
    exit 1
  fi
done

if [[ "$SKIP_E2E" == "1" ]]; then
  echo
  echo "[5/5] Playwright walkthrough E2E — skipped (SKIP_E2E=1)"
else
  echo
  echo "[5/5] Playwright walkthrough E2E (mocked — phase61 + phase14, local webServer)"
  cd "${ROOT}/frontend"
  # E2E uses route mocks — must not inherit remote PLAYWRIGHT_BASE_URL from curl probes.
  env -u PLAYWRIGHT_BASE_URL -u PLAYWRIGHT_NO_WEBSERVER \
    E2E_PHASE61_SUPERVISOR=1 CI=1 \
    npx playwright test e2e/phase61-supervisor-control.spec.ts --workers=1
  env -u PLAYWRIGHT_BASE_URL -u PLAYWRIGHT_NO_WEBSERVER \
    E2E_PHASE14_OPERATOR_FLOWS=1 CI=1 \
    npm run test:e2e:phase14 -- --workers=1
  env -u PLAYWRIGHT_BASE_URL -u PLAYWRIGHT_NO_WEBSERVER \
    E2E_OPERATOR_HUB=1 CI=1 \
    npm run test:e2e:operator-hub -- --workers=1
  cd "${ROOT}"
fi

echo
echo "== Prod walkthrough gate: OK (automated slice) =="
echo "Complete manual steps: docs/AUTHENTICATED_PROD_WALKTHROUGH.md"
