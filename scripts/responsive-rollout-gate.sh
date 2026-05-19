#!/usr/bin/env bash
# Responsive + PWA rollout verification gate (local dev server or remote hive).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND="$ROOT/frontend"

echo "== Queenswarm responsive rollout gate =="

cd "$FRONTEND"
npm run test
npm run typecheck

if [[ -n "${PLAYWRIGHT_BASE_URL:-}" ]]; then
  export PLAYWRIGHT_NO_WEBSERVER=1
  echo "Remote hive: $PLAYWRIGHT_BASE_URL"
  CI=true npx playwright test e2e/pwa-shell.spec.ts
  CI=true npx playwright test e2e/responsive-shell.spec.ts --grep "public login"
else
  CI=true npx playwright test e2e/responsive-shell.spec.ts e2e/responsive-visual.spec.ts e2e/pwa-shell.spec.ts
fi

echo "== Responsive rollout gate: OK =="
