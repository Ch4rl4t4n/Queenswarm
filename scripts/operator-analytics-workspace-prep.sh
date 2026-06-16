#!/usr/bin/env bash
# Operator prep — Analytics Workspace (Track L DA12).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== Analytics Workspace operator prep ==="
echo ""
echo "Manual: docs/OPERATOR_ANALYTICS_WORKSPACE_MANUAL.md"
echo "Route:  https://queenswarm.love/apps-tools/analytics"
echo ""
echo "Checklist:"
echo "  [ ] GA4 connector active (Integrations → ga4_data)"
echo "  [ ] Google Sheets read-only (optional)"
echo "  [ ] business-analytics-report template reviewed (Swarm Builder)"
echo "  [ ] Question wizard dispatch tested"
echo "  [ ] Report critic ≥4/5 before export simulate"
echo ""

if [[ -f "${ROOT}/.env.prod" ]]; then
  echo "Env probe (.env.prod flags):"
  grep -E '^ANALYTICS_' "${ROOT}/.env.prod" 2>/dev/null | head -12 || echo "  (no ANALYTICS_* keys in .env.prod — using defaults)"
  echo ""
fi

"${ROOT}/scripts/audit-analytics-workspace-gate.sh"

echo ""
echo "E2E journey (local, mocked):"
echo "  cd frontend && npx playwright test e2e/analytics-workspace-journey.spec.ts"
