#!/usr/bin/env bash
# Production sign-off gate — orchestrates validation before declaring rollout complete.
#
# Usage:
#   ./scripts/production-signoff-gate.sh
#   PLAYWRIGHT_BASE_URL=https://queenswarm.love ./scripts/production-signoff-gate.sh
#   STRICT_STRIPE=1 ./scripts/production-signoff-gate.sh   # fail when Stripe keys missing
#
# Env:
#   ENV_FILE              — default .env.prod
#   PLAYWRIGHT_BASE_URL   — when set, PWA/responsive E2E hit remote hive (no local webserver)
#   SKIP_BACKEND_TESTS=1  — skip pytest (faster smoke)
#   STRICT_STRIPE=1       — fail if skill marketplace Stripe keys are empty
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
STRICT_STRIPE="${STRICT_STRIPE:-0}"
SKIP_BACKEND_TESTS="${SKIP_BACKEND_TESTS:-0}"
HIVE_BASE="${PLAYWRIGHT_BASE_URL:-https://queenswarm.love}"

load_kv() {
  local file="$1" key="$2"
  local line val
  [[ -f "$file" ]] || return 1
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    if [[ "$line" =~ ^${key}= ]]; then
      val="${line#*=}"
      val="${val%$'\r'}"
      if [[ "$val" == \"*\" ]]; then
        val="${val:1:-1}"
      fi
      printf '%s' "$val"
      return 0
    fi
  done <"$file"
  return 1
}

echo "== Queenswarm production sign-off gate =="
echo "env: ${ENV_FILE}"
echo "hive: ${HIVE_BASE}"
echo

echo "[1/6] validate-prod-env"
./scripts/validate-prod-env.sh

echo
echo "[2/6] core-reliability-gate"
ENV_FILE="$ENV_FILE" ./scripts/core-reliability-gate.sh

if [[ "$SKIP_BACKEND_TESTS" != "1" ]]; then
  echo
  echo "[3/6] backend pytest + coverage"
  (
    cd backend
    PLUGIN_USER_DIR=/tmp/queenswarm-plugins/user \
      python -m pytest -q --cov=app --cov-config=.coveragerc --cov-fail-under=50
  )
else
  echo
  echo "[3/6] backend pytest — skipped (SKIP_BACKEND_TESTS=1)"
fi

echo
echo "[4/6] responsive + PWA gate"
PLAYWRIGHT_BASE_URL="$HIVE_BASE" ./scripts/responsive-rollout-gate.sh

echo
echo "[5/6] prod edge smoke (public routes)"
for path in /health /api/v1/health /health/ready /manifest.webmanifest /sw.js /offline; do
  code="$(curl -sS -o /dev/null -w '%{http_code}' "${HIVE_BASE}${path}" || echo "000")"
  if [[ "$code" != "200" && "$code" != "307" ]]; then
    echo "FAIL ${path} HTTP ${code}" >&2
    exit 1
  fi
  echo "  OK ${path} (${code})"
done

# Phase 14 APIs should exist (401/403 without JWT — not 404).
for path in /api/v1/foragers /api/v1/paper-trading/summary; do
  code="$(curl -sS -o /dev/null -w '%{http_code}' "${HIVE_BASE}${path}" || echo "000")"
  if [[ "$code" == "404" || "$code" == "000" ]]; then
    echo "FAIL ${path} HTTP ${code} (expected auth gate, not missing route)" >&2
    exit 1
  fi
  echo "  OK ${path} (${code} — route wired)"
done

echo
echo "[6/6] Stripe + Phase 14 feature readiness"
if [[ -x "${ROOT}/scripts/stripe-prod-setup.sh" ]]; then
  ./scripts/stripe-prod-setup.sh || {
    if [[ "$STRICT_STRIPE" == "1" ]]; then
      exit 1
    fi
  }
fi

for flag in PAPER_TRADING_ENABLED PENDING_REVIEW_ENABLED RECIPES_ENABLED SKILL_EXPORT_PREMIUM_ENABLED; do
  val="$(load_kv "$ENV_FILE" "$flag" 2>/dev/null || echo "unset")"
  echo "  ${flag}=${val:-unset}"
done

echo
echo "== Production sign-off gate: OK =="
echo "Manual QA still recommended:"
echo "  • Mobile: 2× visit → install prompt; airplane mode → offline banner"
echo "  • Desktop: sidebar-only shell; Ballroom FAB bottom-right (Ctrl+B)"
echo "  • Stripe: complete checkout once keys are configured"
