#!/usr/bin/env bash
# Operator CLI — download verified Alpaca JSONL (Track M LOC5).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BASE_URL="${QUEENSWARM_BASE_URL:-https://queenswarm.love}"
JWT="${OPERATOR_SMOKE_JWT:-}"

if [[ -z "${JWT}" ]]; then
  echo "Set OPERATOR_SMOKE_JWT to a dashboard bearer token." >&2
  exit 1
fi

OUT="${1:-queenswarm-verified-dataset.jsonl}"
curl -fsSL \
  -H "Authorization: Bearer ${JWT}" \
  "${BASE_URL}/api/v1/llm-routing/verified-dataset/export" \
  -o "${OUT}"

ROWS="$(wc -l < "${OUT}" | tr -d ' ')"
echo "Wrote ${OUT} (${ROWS} JSONL row(s))"
