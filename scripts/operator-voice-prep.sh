#!/usr/bin/env bash
# ST8 JA7 — Voice prep (Grok live + STT/TTS prefs); keys optional via ST8_JA7_REQUIRE_KEYS=0.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

REQUIRE_KEYS="${ST8_JA7_REQUIRE_KEYS:-0}"
ENV_FILE="${ENV_FILE:-.env.prod}"

echo "=== ST8 JA7 Voice prep ==="

for f in \
  backend/app/application/services/voice_multimodal.py \
  backend/app/presentation/api/routers/realtime_ballroom.py \
  frontend/components/ballroom/grok-live-voice-chat.tsx \
  scripts/voice-readiness-gate.sh; do
  if [[ -f "$f" ]]; then
    echo "  OK  $f"
  else
    echo "  FAIL missing $f" >&2
    exit 1
  fi
done

if [[ "$REQUIRE_KEYS" == "1" ]]; then
  ENV_FILE="$ENV_FILE" ./scripts/voice-readiness-gate.sh
else
  echo "  SKIP runtime keys (ST8_JA7_REQUIRE_KEYS=0) — enable VOICE_ENABLED + provider keys for live voice"
fi

echo "JA7 VOICE PREP: OK"
