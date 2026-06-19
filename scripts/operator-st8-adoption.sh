#!/usr/bin/env bash
# ST8 operator adoption — voice, Slack, GitHub, learn-from-source, Track M gates.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ST8 Personal OS optional ops (explicit opt-in shipped)   ║"
echo "╚══════════════════════════════════════════════════════════╝"

ST8_JA7_REQUIRE_KEYS=0 ./scripts/operator-voice-prep.sh
./scripts/operator-slack-alertmanager-prep.sh || true
./scripts/operator-github-webhook-prep.sh || true

echo ""
./scripts/audit-personal-os-st8-gate.sh
