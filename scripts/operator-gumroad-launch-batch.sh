#!/usr/bin/env bash
# POS-Y — Operator Gumroad launch batch (manual upload + optional API on commercial host).
#
# Usage:
#   ./scripts/operator-gumroad-launch-batch.sh
#   LIMIT=5 ./scripts/operator-gumroad-launch-batch.sh
#   TOKEN=... HIVE_BASE=https://queenswarm.love ./scripts/operator-gumroad-launch-batch.sh --api-draft
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LIMIT="${LIMIT:-3}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
ENV_FILE="${ENV_FILE:-.env.prod}"
API_DRAFT=0

for arg in "$@"; do
  case "$arg" in
    --api-draft) API_DRAFT=1 ;;
  esac
done

echo "== Operator Gumroad launch batch (limit=${LIMIT}) =="

"$ROOT/scripts/prepare-launch-batch.sh" "$LIMIT"

OUT="$ROOT/exports/launch-batch"
UP="$ROOT/exports/gumroad-upload"

echo ""
echo "-- Manual Gumroad upload lane --"
if [[ -f "$OUT/LAUNCH_CHECKLIST.md" ]]; then
  echo "Checklist: $OUT/LAUNCH_CHECKLIST.md"
fi
if compgen -G "$UP/*.tar.gz" >/dev/null; then
  echo "Tarballs:"
  ls -1 "$UP"/*.tar.gz
else
  echo "No tarballs in $UP — approve sellable skills and re-run."
fi

if [[ "$API_DRAFT" -eq 0 ]]; then
  echo ""
  echo "API draft skipped (default Personal OS). Re-run with --api-draft when commercial host + token ready."
  exit 0
fi

TOKEN="${TOKEN:-${OPERATOR_SMOKE_JWT:-}}"
if [[ -z "$TOKEN" ]] && [[ -f "$ENV_FILE" ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^OPERATOR_SMOKE_JWT= ]] || continue
    TOKEN="${line#OPERATOR_SMOKE_JWT=}"
    TOKEN="${TOKEN%$'\r'}"
    TOKEN="${TOKEN#\"}"
    TOKEN="${TOKEN%\"}"
    break
  done <"$ENV_FILE"
fi

if [[ -z "$TOKEN" ]]; then
  echo "WARN: TOKEN / OPERATOR_SMOKE_JWT missing — cannot call Gumroad draft API."
  exit 0
fi

echo ""
echo "-- Gumroad draft API (commercial host only) --"
code="$(curl -sS -o /tmp/gumroad-draft-batch.json -w '%{http_code}' \
  -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  "${HIVE_BASE}/api/v1/dashboard/factory-launch/gumroad-draft?limit=${LIMIT}" \
  2>/dev/null || echo 000)"

if [[ "$code" == "404" ]]; then
  echo "Commercial API archived (Personal OS) — use manual upload lane above."
  exit 0
fi

if [[ "$code" != "200" && "$code" != "201" ]]; then
  echo "Gumroad draft batch failed HTTP ${code}"
  cat /tmp/gumroad-draft-batch.json 2>/dev/null || true
  exit 1
fi

python3 -m json.tool /tmp/gumroad-draft-batch.json 2>/dev/null || cat /tmp/gumroad-draft-batch.json
echo "== Operator Gumroad launch batch: DONE =="
