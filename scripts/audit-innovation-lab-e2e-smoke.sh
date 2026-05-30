#!/usr/bin/env bash
# Innovation Lab E2E smoke — research-to-pr-proposal → approve → Maintainer handoff.
#
# Usage:
#   ./scripts/audit-innovation-lab-e2e-smoke.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${ROOT}/backend/venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="python3"
fi

echo "=== Innovation Lab E2E Smoke ==="

cd "${ROOT}/backend"
"$PY" -m pytest tests/test_hive_innovation_lab_unit.py -q --no-cov

echo ""
echo "INNOVATION LAB E2E SMOKE: PASS"
