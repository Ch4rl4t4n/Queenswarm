#!/usr/bin/env bash
# Close Operator P0 — run production signoff + handoff refresh.
#
# Usage:
#   ./scripts/operator-p0-close.sh
#   SKIP_SIGNOFF=1 ./scripts/operator-p0-close.sh   # skip production-signoff-gate
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Queenswarm Operator P0 Close                            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo

echo "[1/3] production signoff gate"
./scripts/production-signoff-gate.sh
echo

echo "[2/3] operator launch gate (automated slice)"
SKIP_E2E=1 SKIP_RESPONSIVE_E2E=1 ./scripts/operator-launch-gate.sh
echo

echo "[3/3] final handoff + Hetzner reminder"
SKIP_E2E=1 SKIP_RESPONSIVE_E2E=1 ./scripts/operator-final-handoff.sh
echo
./scripts/operator-hetzner-send-prep.sh

echo
echo "== Operator P0 close: COMPLETE =="
echo "Remaining human step: send Hetzner email (see above)."
