#!/usr/bin/env bash
# Quick SLO conformance check against production edge endpoints.
set -euo pipefail

BASE_URL="${BASE_URL:-https://queenswarm.love}"
SAMPLES_PER_PATH="${SAMPLES_PER_PATH:-20}"
MAX_P95_MS="${MAX_P95_MS:-800}"
MIN_SUCCESS_RATE="${MIN_SUCCESS_RATE:-0.995}"
REPORT_DIR="${REPORT_DIR:-./reports/slo}"

mkdir -p "${REPORT_DIR}"
stamp="$(date -u +'%Y%m%dT%H%M%SZ')"
csv_file="${REPORT_DIR}/slo-${stamp}.csv"
md_file="${REPORT_DIR}/slo-${stamp}.md"
echo "path,http_code,latency_ms" > "${csv_file}"

paths=("/health" "/api/v1/health" "/health/ready")

for path in "${paths[@]}"; do
  for _ in $(seq 1 "${SAMPLES_PER_PATH}"); do
    line="$(curl -sS -o /dev/null -w "%{http_code},%{time_total}" "${BASE_URL}${path}" || echo "000,9.999")"
    code="${line%,*}"
    sec="${line#*,}"
    ms="$(python3 - <<PY
print(int(float("${sec}") * 1000))
PY
)"
    echo "${path},${code},${ms}" >> "${csv_file}"
  done
done

python3 <<PY
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
import statistics
import sys

rows = list(csv.DictReader(Path("${csv_file}").open()))
grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
for row in rows:
    grouped[row["path"]].append(row)

lines = [
    "# SLO Check Report",
    "",
    f"Base URL: ${BASE_URL}",
    f"Samples/path: ${SAMPLES_PER_PATH}",
    f"Thresholds: success_rate >= ${MIN_SUCCESS_RATE}, p95_ms <= ${MAX_P95_MS}",
    "",
    "| Path | Samples | Success rate | Avg ms | P95 ms | Status |",
    "|---|---:|---:|---:|---:|---|",
]
global_ok = True
for path, items in sorted(grouped.items()):
    latencies = [int(item["latency_ms"]) for item in items]
    success = 0
    for item in items:
        code = int(item["http_code"])
        if code in (200, 204, 301, 302, 307, 308, 503):
            success += 1
    rate = success / len(items)
    p95 = statistics.quantiles(latencies, n=20)[-1] if len(latencies) > 1 else latencies[0]
    avg = int(sum(latencies) / len(latencies))
    ok = rate >= float("${MIN_SUCCESS_RATE}") and p95 <= float("${MAX_P95_MS}")
    status = "PASS" if ok else "FAIL"
    lines.append(f"| {path} | {len(items)} | {rate:.4f} | {avg} | {int(p95)} | {status} |")
    if not ok:
        global_ok = False

Path("${md_file}").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
print(f"Report: ${md_file}")
if not global_ok:
    sys.exit(1)
PY
