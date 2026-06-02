#!/usr/bin/env bash
# Configure + verify YouTube Data API v3 key for Social Intel scrape.
#
# Usage:
#   ./scripts/operator-youtube-api-setup.sh              # check only
#   YOUTUBE_API_KEY=AIza... ./scripts/operator-youtube-api-setup.sh
#   YOUTUBE_API_KEY=AIza... REDEPLOY=1 SCRAPE=1 ./scripts/operator-youtube-api-setup.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
REDEPLOY="${REDEPLOY:-1}"
SCRAPE="${SCRAPE:-0}"
TEST_CHANNEL="${TEST_CHANNEL:-@ycombinator}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  YouTube Data API v3 — Social Intel setup                 ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo

if [[ -z "${YOUTUBE_API_KEY:-}" ]] && [[ -f "${ROOT}/${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ROOT}/${ENV_FILE}" 2>/dev/null || true
fi

if [[ -z "${YOUTUBE_API_KEY:-}" ]]; then
  cat <<'GUIDE'

Kľúč ešte nie je nastavený. Postup v Google Cloud (5–10 min):

  1. https://console.cloud.google.com/ → vyber/vytvor projekt
  2. APIs & Services → Library → „YouTube Data API v3“ → Enable
  3. APIs & Services → Credentials → Create credentials → API key
  4. (Odporúčané) Restrict key → API restrictions → len YouTube Data API v3
  5. Skopíruj kľúč a spusti:

     YOUTUBE_API_KEY=AIzaSy... REDEPLOY=1 SCRAPE=1 ./scripts/operator-youtube-api-setup.sh

  Alebo mi kľúč pošli v chate — doplním do .env.prod a redeploynem (nikdy ho necommitujeme).

GUIDE
  exit 1
fi

# Persist to .env.prod (replace or append)
ENV_PATH="${ROOT}/${ENV_FILE}"
if grep -q '^# YOUTUBE_API_KEY=' "${ENV_PATH}" 2>/dev/null; then
  sed -i "s|^# YOUTUBE_API_KEY=.*|YOUTUBE_API_KEY=${YOUTUBE_API_KEY}|" "${ENV_PATH}"
elif grep -q '^YOUTUBE_API_KEY=' "${ENV_PATH}" 2>/dev/null; then
  sed -i "s|^YOUTUBE_API_KEY=.*|YOUTUBE_API_KEY=${YOUTUBE_API_KEY}|" "${ENV_PATH}"
else
  printf '\nYOUTUBE_API_KEY=%s\n' "${YOUTUBE_API_KEY}" >> "${ENV_PATH}"
fi
echo "OK  YOUTUBE_API_KEY written to ${ENV_FILE}"

# Live API probe (read-only)
HTTP_CODE=$(curl -sS -o /tmp/yt_probe.json -w "%{http_code}" \
  "https://www.googleapis.com/youtube/v3/channels?part=id&forHandle=${TEST_CHANNEL#@}&key=${YOUTUBE_API_KEY}")

if [[ "${HTTP_CODE}" == "200" ]] && grep -q '"items"' /tmp/yt_probe.json 2>/dev/null; then
  echo "OK  YouTube API probe (${TEST_CHANNEL}) — HTTP 200"
  rm -f /tmp/yt_probe.json
elif [[ "${HTTP_CODE}" == "403" ]]; then
  echo "FAIL YouTube API 403 — enable YouTube Data API v3 alebo skontroluj quota/restrictions"
  head -c 200 /tmp/yt_probe.json 2>/dev/null; echo
  rm -f /tmp/yt_probe.json
  exit 1
else
  echo "WARN YouTube API probe HTTP ${HTTP_CODE} — skontroluj kľúč"
  head -c 200 /tmp/yt_probe.json 2>/dev/null; echo
  rm -f /tmp/yt_probe.json
fi

if [[ "${REDEPLOY}" == "1" ]]; then
  echo ""
  echo "Redeploy backend + celery…"
  docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml \
    --env-file "${ENV_FILE}" up -d --build backend celery-worker celery-beat --wait
  docker exec "${BACKEND}" python -c "from app.core.config import settings; assert settings.youtube_api_key; print('OK  backend sees youtube_api_key')"
fi

if [[ "${SCRAPE}" == "1" ]]; then
  echo ""
  echo "Starting backfill scrape (40 channels — môže trvať dlho)…"
  SCRAPE=1 "${ROOT}/scripts/operator-social-intel-provision.sh"
fi

echo ""
echo "Done. Daily delta: Celery beat 07:30 UTC."
