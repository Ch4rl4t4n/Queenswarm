#!/usr/bin/env bash
# Run automated walkthrough gate and persist JSON evidence for operator sign-off.
#
# Usage:
#   ./scripts/walkthrough-evidence.sh
#   OPERATOR_BEARER_TOKEN=... ./scripts/walkthrough-evidence.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
REPORT_DIR="${REPORT_DIR:-./reports/walkthrough}"
stamp="$(date -u +'%Y%m%dT%H%M%SZ')"
json_report="${REPORT_DIR}/walkthrough-${stamp}.json"
log_file="$(mktemp)"

mkdir -p "${REPORT_DIR}"

echo "== Walkthrough evidence run =="
echo "hive: ${HIVE_BASE}"
echo

set +e
SKIP_E2E=1 HIVE_BASE="${HIVE_BASE}" ./scripts/prod-walkthrough-gate.sh >"${log_file}" 2>&1
gate_exit=$?
set -e

cat "${log_file}"

ready_code="$(curl -sS -o /dev/null -w '%{http_code}' "${HIVE_BASE}/health/ready" 2>/dev/null || echo "000")"
passed=$([[ "${gate_exit}" -eq 0 ]] && echo true || echo false)
user_jwt_auto=false
if grep -q "authenticated user smoke (auto user JWT" "${log_file}" 2>/dev/null; then
  user_jwt_auto=true
fi
user_jwt_skipped=false
if grep -q "authenticated user smoke — skipped" "${log_file}" 2>/dev/null; then
  user_jwt_skipped=true
fi

cat > "${json_report}" <<EOF
{
  "timestamp_utc": "${stamp}",
  "hive_base": "${HIVE_BASE}",
  "walkthrough_gate_exit": ${gate_exit},
  "passed": ${passed},
  "health_ready_code": ${ready_code},
  "user_jwt_auto_minted": ${user_jwt_auto},
  "user_jwt_skipped": ${user_jwt_skipped},
  "report_file": "$(basename "${json_report}")",
  "log_excerpt": $(python3 -c "import json, pathlib; print(json.dumps(pathlib.Path('${log_file}').read_text()[-1200:]))")
}
EOF

rm -f "${log_file}"

echo
echo "[walkthrough-evidence] wrote ${json_report}"

if [[ "${gate_exit}" -ne 0 ]]; then
  exit "${gate_exit}"
fi

echo "[walkthrough-evidence] automated slice passed"
