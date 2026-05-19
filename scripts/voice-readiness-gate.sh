#!/usr/bin/env bash
# Server-side voice readiness gate (STT + TTS prerequisites).
#
# Required for "Voice Chat with Orchestrator" in production:
# - VOICE_ENABLED=true
# - STT provider configured (Grok, Deepgram, or OpenAI key)
# - TTS provider configured (Grok, ElevenLabs, or OpenAI key)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
PROJECT="${PROJECT:-queenswarm_prod}"

backend_id="$(docker compose -p "$PROJECT" -f docker-compose.base.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" ps -q backend)"
if [[ -z "${backend_id// }" ]]; then
  echo "voice-gate: backend container not found for ${PROJECT}"
  exit 1
fi

docker exec "$backend_id" sh -lc "python - <<'PY'
from app.core.config import settings
from app.application.services.llm_runtime_credentials import (
    provider_effective_deepgram,
    provider_effective_elevenlabs,
    provider_effective_grok,
    provider_effective_openai,
)

voice_enabled = bool(settings.voice_enabled)
openai_present = bool(provider_effective_openai().strip())
deepgram_present = bool(provider_effective_deepgram().strip())
eleven_present = bool(provider_effective_elevenlabs().strip())
grok_present = bool(provider_effective_grok().strip())
stt_ready = bool(voice_enabled and (grok_present or deepgram_present or openai_present))
tts_ready = bool(voice_enabled and (grok_present or openai_present or eleven_present))

print({
    'voice_enabled': voice_enabled,
    'grok_key_present': grok_present,
    'openai_key_present': openai_present,
    'deepgram_key_present': deepgram_present,
    'elevenlabs_key_present': eleven_present,
    'stt_ready': stt_ready,
    'tts_ready': tts_ready,
})

if not voice_enabled:
    raise SystemExit(2)
if not stt_ready:
    raise SystemExit(3)
if not tts_ready:
    raise SystemExit(4)
PY"

echo "voice-gate: PASS"
