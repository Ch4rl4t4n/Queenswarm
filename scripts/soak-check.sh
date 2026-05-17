#!/usr/bin/env bash
# Production soak probe: repeated health/API requests with latency/error summary.
set -euo pipefail

BASE_URL="${BASE_URL:-https://queenswarm.love}"
DURATION_MIN="${DURATION_MIN:-30}"
SLEEP_SEC="${SLEEP_SEC:-0.2}"
MAX_P95_MS="${MAX_P95_MS:-1200}"
MIN_SUCCESS_RATE="${MIN_SUCCESS_RATE:-0.99}"
REPORT_DIR="${REPORT_DIR:-./reports/soak}"

mkdir -p "${REPORT_DIR}"
stamp="$(date -u +'%Y%m%dT%H%M%SZ')"
log_file="${REPORT_DIR}/soak-${stamp}.csv"

echo "timestamp,path,http_code,latency_ms" > "${log_file}"
end_ts=$(( $(date +%s) + DURATION_MIN * 60 ))

paths=("/health" "/api/v1/health" "/health/ready")

echo "[soak] base=${BASE_URL} duration=${DURATION_MIN}min output=${log_file}"
while [[ "$(date +%s)" -lt "${end_ts}" ]]; do
  for path in "${paths[@]}"; do
    line="$(curl -sS -o /dev/null -w "%{http_code},%{time_total}" "${BASE_URL}${path}" || echo "000,9.999")"
    code="${line%,*}"
    sec="${line#*,}"
    ms="$(python3 - <<PY
sec = float("${sec}")
print(int(sec * 1000))
PY
)"
    echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ'),${path},${code},${ms}" >> "${log_file}"
  done
  sleep "${SLEEP_SEC}"
done

python3 <<PY
from __future__ import annotations

import csv
from pathlib import Path
import statistics
import sys

log_path = Path("${log_file}")
rows = list(csv.DictReader(log_path.open()))
if not rows:
    print("[soak] no rows captured")
    sys.exit(1)

latencies = [int(r["latency_ms"]) for r in rows]
ok = 0
for row in rows:
    code = int(row["http_code"])
    if code in (200, 204, 301, 302, 307, 308, 503):
        ok += 1

success_rate = ok / len(rows)
p95 = statistics.quantiles(latencies, n=20)[-1] if len(latencies) > 1 else latencies[0]
avg = int(sum(latencies) / len(latencies))
print(f"[soak] samples={len(rows)} success_rate={success_rate:.4f} avg_ms={avg} p95_ms={int(p95)}")

if success_rate < float("${MIN_SUCCESS_RATE}"):
    print(f"[soak] FAIL success_rate < ${MIN_SUCCESS_RATE}")
    sys.exit(1)
if p95 > float("${MAX_P95_MS}"):
    print(f"[soak] FAIL p95_ms > ${MAX_P95_MS}")
    sys.exit(1)
print("[soak] PASS")
PY
