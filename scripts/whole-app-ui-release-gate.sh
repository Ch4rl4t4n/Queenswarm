#!/usr/bin/env bash
# Whole-App UI Reorder — release gate (typecheck + unit + E2E + optional extended + health).
#
# Env:
#   WHOLE_APP_EXTENDED_GATE=1   — append responsive-shell + responsive-visual E2E
#   WHOLE_APP_EXTENDED_ONLY=1   — extended E2E only (CI visual job)
#   SKIP_HEALTH_CHECK=1         — skip prod health probe
#   PLAYWRIGHT_WORKERS=1        — serial Playwright (recommended in CI)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND="${ROOT}/frontend"
FAIL=0
RUN_EXTENDED="${WHOLE_APP_EXTENDED_GATE:-0}"
EXTENDED_ONLY="${WHOLE_APP_EXTENDED_ONLY:-0}"
SKIP_CORE="${WHOLE_APP_SKIP_CORE:-0}"

if [[ "$EXTENDED_ONLY" == "1" ]]; then
  RUN_EXTENDED=1
  SKIP_CORE=1
fi

pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=1; }

echo "=== Whole-App UI Release Gate (${HIVE_RELEASE_GATE_LABEL:-2026.05-v5}) ==="
if [[ "$EXTENDED_ONLY" == "1" ]]; then
  echo "(extended visual only — WHOLE_APP_EXTENDED_ONLY=1)"
fi

if [[ "$SKIP_CORE" != "1" ]]; then
  echo ""
  echo "--- frontend typecheck ---"
  if (cd "$FRONTEND" && npx tsc --noEmit); then
    pass "tsc --noEmit"
  else
    fail "tsc --noEmit"
  fi

  echo ""
  echo "--- whole-app unit tests ---"
  UNIT_FILES=(
    lib/hive-ia-canonical.test.ts
    lib/hive-page-zone-spec.test.ts
    lib/hive-critical-journeys-spec.test.ts
    lib/hive-release-gate-spec.test.ts
    lib/hive-page-error.test.ts
    lib/hive-page-performance-spec.test.ts
    lib/hive-a11y.test.ts
    lib/hive-mobile-meta.test.ts
    lib/mobile-tablet-zone-spec.test.ts
    lib/mobile-tablet-chrome.test.ts
    lib/dead-button-audit.test.ts
    lib/execution-lane-routes.test.ts
    lib/factory-content-factory-routes.test.ts
    lib/settings-nav.test.ts
    lib/settings-nav-tiers.test.ts
    lib/hive-prod-journey-spec.test.ts
    lib/hive-modal-migration-spec.test.ts
    lib/hive-modal-shell.test.ts
    lib/hive-popover-position.test.ts
    lib/hive-popover-spec.test.ts
    lib/billing-settings-copy.test.ts
  )
  if (cd "$FRONTEND" && npm run test -- --run "${UNIT_FILES[@]}"); then
    pass "vitest whole-app unit bundle"
  else
    fail "vitest whole-app unit bundle"
  fi

  echo ""
  echo "--- whole-app E2E specs ---"
  E2E_SPECS=(
    whole-app-ia.spec.ts
    whole-app-page-shell.spec.ts
    whole-app-settings-disclosure.spec.ts
    whole-app-settings-density.spec.ts
    whole-app-dead-buttons.spec.ts
    whole-app-cross-route-naming.spec.ts
    whole-app-mobile-tablet.spec.ts
    whole-app-a11y.spec.ts
    whole-app-performance.spec.ts
    whole-app-critical-journeys.spec.ts
    whole-app-release-gate.spec.ts
  )
  for spec in "${E2E_SPECS[@]}"; do
    echo "  · e2e/${spec}"
    if (cd "$FRONTEND" && npx playwright test "e2e/${spec}" --workers="${PLAYWRIGHT_WORKERS:-1}"); then
      pass "e2e/${spec}"
    else
      fail "e2e/${spec}"
    fi
  done
fi

if [[ "$RUN_EXTENDED" == "1" ]]; then
  echo ""
  echo "--- extended responsive visual gate ---"
  for spec in responsive-shell.spec.ts responsive-visual.spec.ts; do
    echo "  · e2e/${spec}"
    if (cd "$FRONTEND" && CI="${CI:-true}" npx playwright test "e2e/${spec}" --workers="${PLAYWRIGHT_WORKERS:-1}"); then
      pass "e2e/${spec}"
    else
      fail "e2e/${spec}"
    fi
  done
fi

if [[ "$SKIP_CORE" != "1" ]]; then
  echo ""
  echo "--- production health (optional) ---"
  ENV_FILE="${PRD_ENV_FILE:-${ROOT}/.env.prod}"
  if [[ -f "$ENV_FILE" ]] && [[ "${SKIP_HEALTH_CHECK:-0}" != "1" ]]; then
    if PRD_ENV_FILE="$ENV_FILE" "${ROOT}/scripts/health-check.sh"; then
      pass "health-check.sh"
    else
      fail "health-check.sh"
    fi
  else
    echo "  skip health (set PRD_ENV_FILE or SKIP_HEALTH_CHECK=0 to probe prod)"
  fi
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "WHOLE-APP UI RELEASE GATE: PASS"
  if [[ "$EXTENDED_ONLY" != "1" ]]; then
    echo "Manual visual QA: spot-check /agentic-os, /swarms, /apps-tools on desktop + mobile."
  fi
  exit 0
fi
echo "WHOLE-APP UI RELEASE GATE: FAIL"
exit 1
