#!/usr/bin/env bash
# POS-CE gate — verify community engagement assets exist (no prod secrets).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail=0

check_file() {
  if [[ -f "$1" ]]; then
    echo "OK  $1"
  else
    echo "MISS $1"
    fail=1
  fi
}

check_grep() {
  if grep -q "$2" "$1" 2>/dev/null; then
    echo "OK  $1 contains $2"
  else
    echo "MISS $1 missing $2"
    fail=1
  fi
}

echo "=== Community Engagement (POS-CE) gate ==="
check_file "backend/app/skills/community-engagement-playbook.md"
check_file "backend/app/application/services/community_engagement_policy.py"
check_file "backend/scripts/seed_community_engagement.py"
check_file "docs/COMMUNITY_ENGAGEMENT_SETUP.md"
check_grep "backend/app/application/services/rubric_templates.py" "community-authenticity"
check_grep "backend/app/application/services/data_monitor_wizard_service.py" '"community"'
check_grep "backend/app/application/services/solo_operator_four_lanes.py" "community-engagement-playbook"

if [[ "${fail}" -ne 0 ]]; then
  echo ""
  echo "FAIL — fix missing POS-CE assets"
  exit 1
fi

echo ""
echo "PASS — run ./scripts/operator-community-engagement-provision.sh to provision tenant"
