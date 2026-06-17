#!/usr/bin/env bash
# POS-G prep — inventory commercial/dead routes for future deletion (read-only, no deletes).
#
# Run after 2 weeks stable Personal OS. Output guides POS-G deletion PR.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT="${REPORT:-./reports/operator/personal-os-dead-code-inventory-${STAMP}.txt}"

mkdir -p "$(dirname "$REPORT")"

{
  echo "Personal OS dead-code inventory (POS-G prep)"
  echo "Generated: ${STAMP}"
  echo "Policy: hide-first — delete only after 2 weeks stable Personal OS"
  echo ""
  echo "=== Candidate backend routers (commercial/revenue) ==="
  rg -l 'gumroad|revenue_funnel|factory_launch|trading_cockpit|catalog_wave' \
    backend/app/presentation/api/routers/ 2>/dev/null | sort || true
  echo ""
  echo "=== Candidate frontend routes (factory/revenue/trading) ==="
  find frontend/app -type f \( -path '*factory*' -o -path '*trading*' -o -path '*revenue*' \) 2>/dev/null | sort || true
  echo ""
  echo "=== Mission Home revenue widgets (should stay gated, not deleted until POS-G) ==="
  rg -n 'revenue_funnel|factory_launch|catalog_wave|RevenueFunnel|FactoryLaunch|CatalogWave' \
    frontend/components/hive/mission-home-panel.tsx 2>/dev/null || true
  echo ""
  echo "=== Gumroad/commercial Skill Factory (lite gate hides — delete in POS-G) ==="
  rg -n 'gumroad|Gumroad|launch_queue|SkillFactoryRevenueFunnel' \
    frontend/components/apps-tools/skill-factory-page-client.tsx 2>/dev/null | head -30 || true
  echo ""
  echo "=== POS audit gates to re-run before deletion ==="
  echo "  ./scripts/operator-personal-os-verify.sh"
  echo "  ./scripts/audit-personal-os-dead-code-inventory.sh > review.txt"
  echo ""
  echo "=== Suggested POS-G deletion order (when ready) ==="
  echo "  1. Remove unused /factory route + factory-launch-widget from Mission Home"
  echo "  2. Strip Gumroad export endpoints if personal_os-only host permanently"
  echo "  3. Archive revenue-funnel / catalog-wave services behind feature flag removal"
  echo "  4. Do NOT delete marketing-team / faceless / publish-queue (Personal OS core)"
} | tee "$REPORT"

echo ""
echo "Inventory written: ${REPORT}"
