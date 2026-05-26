#!/usr/bin/env bash
# One-screen Virtual Company solo status (read-only).
#
# Usage:
#   ./scripts/operator-vc-status-report.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="${REPORT_DIR:-./reports/operator}"
JSON_OUT="${REPORT_DIR}/vc-status-${STAMP}.json"

mkdir -p "$REPORT_DIR"

if ! docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  echo "Backend not running." >&2
  exit 1
fi

TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null)"
curl -sk -H "Authorization: Bearer ${TOKEN}" \
  "${HIVE_BASE}/api/v1/virtual-company/readiness-audit" | tee "$JSON_OUT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
c = d.get('checklist', {})
fr = c.get('first_run', {})
op = d.get('oauth_progress') or c.get('oauth_progress') or {}
print('== Virtual Company status ==')
print(f\"Readiness:     {d.get('readiness_score', 0)}%\")
print(f\"Simulate:      {fr.get('completed_count', 0)}/{fr.get('playbooks_total', 6)} playbooks\")
print(f\"OAuth env:     {op.get('configured', 0)}/{op.get('total', 3)} vendors configured\")
print(f\"OAuth connect: {op.get('connected', 0)}/{op.get('total', 3)} connectors active\")
print(f\"Super routers: {c.get('super_routers', {}).get('active', 0)}/{c.get('super_routers', {}).get('provisioned_total', 2)} active\")
print(f\"Dept swarms:   {c.get('swarms', {}).get('departments_built', 0)}/{c.get('swarms', {}).get('departments_total', 6)}\")
print()
blockers = d.get('blockers') or c.get('blockers') or []
simulate_complete = d.get('simulate_path_complete') or c.get('simulate_path_complete', False)
if blockers:
    print('Blockers:')
    for b in blockers:
        print(f'  • {b}')
    print()
elif simulate_complete:
    print('Status: Simulate path COMPLETE — live connectors optional.')
    print('When ready: ./scripts/operator-vc-notion-onboard.sh')
    print()
elif fr.get('completed_count', 0) >= fr.get('playbooks_total', 6):
    if op.get('connected', 0) > 0:
        print('Next: add NOTION_INTEGRATION_TOKEN → APPLY=1 ./scripts/operator-vc-manual-tokens.sh')
        print('      Gmail: Google OAuth in .env.prod.oauth')
    else:
        print('Next: APPLY=1 ./scripts/operator-vc-manual-tokens.sh (gh auth → GitHub) or fill .env.prod.oauth')
elif op.get('env_ready') and not op.get('connectors_ready'):
    print('Next: /integrations?tab=studio → Connect Notion + Gmail + GitHub')
elif d.get('readiness_score', 0) >= 100:
    print('Status: Virtual Company solo path complete.')
" "$JSON_OUT"

echo "Report: ${JSON_OUT}"
