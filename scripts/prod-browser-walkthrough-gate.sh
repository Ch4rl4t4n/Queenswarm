#!/usr/bin/env bash
# Prod browser walkthrough — public pages + authenticated shell (real user JWT).
#
# Usage:
#   ./scripts/prod-browser-walkthrough-gate.sh
#   SKIP_PROD_PUBLIC=1 ./scripts/prod-browser-walkthrough-gate.sh
#   OPERATOR_USER_BEARER_TOKEN=eyJ... ./scripts/prod-browser-walkthrough-gate.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
ENV_FILE="${ENV_FILE:-.env.prod}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="${REPORT_DIR:-${ROOT}/reports/walkthrough}"
JSON_OUT="${REPORT_DIR}/browser-walkthrough-${STAMP}.json"
SKIP_PROD_PUBLIC="${SKIP_PROD_PUBLIC:-0}"
COMPOSE=(docker compose -p queenswarm_prod -f "${ROOT}/docker-compose.base.yml" -f "${ROOT}/docker-compose.prod.yml" --env-file "${ROOT}/${ENV_FILE}")

resolve_operator_user_jwt() {
  if [[ -n "${OPERATOR_USER_BEARER_TOKEN:-}" ]]; then
    printf '%s' "$OPERATOR_USER_BEARER_TOKEN"
    return 0
  fi
  if [[ "${AUTO_OPERATOR_USER_JWT:-1}" != "1" ]] || ! command -v docker >/dev/null 2>&1; then
    return 1
  fi
  local cid token
  cid="$("${COMPOSE[@]}" ps -q backend 2>/dev/null || true)"
  [[ -n "${cid// }" ]] || return 1
  token="$("${COMPOSE[@]}" exec -T backend python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n' || true)"
  [[ -n "${token// }" && "$token" == eyJ* ]] || return 1
  printf '%s' "$token"
}

echo "== Queenswarm prod browser walkthrough gate =="
echo "hive: ${HIVE_BASE}"
echo

resolved_user_jwt=""
if ! resolved_user_jwt="$(resolve_operator_user_jwt)"; then
  resolved_user_jwt=""
fi

cd "${ROOT}/frontend"

if [[ "$SKIP_PROD_PUBLIC" != "1" ]]; then
  echo "[1/2] prod public Playwright (login overflow + lead magnets)"
  PLAYWRIGHT_BASE_URL="${HIVE_BASE}" E2E_PROD_PUBLIC=1 CI=1 \
    npx playwright test e2e/prod-public-walkthrough.spec.ts --workers=1
  echo
else
  echo "[1/2] prod public Playwright — skipped (SKIP_PROD_PUBLIC=1)"
  echo
fi

if [[ -n "${resolved_user_jwt}" ]]; then
  echo "[2/2] prod authenticated Playwright (user JWT — whole-app journey matrix)"
  PLAYWRIGHT_BASE_URL="${HIVE_BASE}" \
    OPERATOR_USER_BEARER_TOKEN="${resolved_user_jwt}" \
    E2E_PROD_AUTHENTICATED=1 CI=1 \
    npx playwright test e2e/whole-app-prod-journeys.spec.ts e2e/prod-authenticated-walkthrough.spec.ts --workers=1
else
  echo "[2/2] prod authenticated Playwright — skipped (no user JWT)"
  exit 1
fi

echo
python3 - <<PY
import json
from pathlib import Path
Path("${REPORT_DIR}").mkdir(parents=True, exist_ok=True)
report = {
    "timestamp_utc": "${STAMP}",
    "hive_base": "${HIVE_BASE}",
    "passed": True,
    "public_playwright": "${SKIP_PROD_PUBLIC}" != "1",
    "authenticated_playwright": True,
    "report_file": Path("${JSON_OUT}").name,
}
Path("${JSON_OUT}").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(f"[browser-walkthrough] wrote ${JSON_OUT}")
PY
echo "== Prod browser walkthrough gate: OK =="
