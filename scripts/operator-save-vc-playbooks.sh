#!/usr/bin/env bash
# Save completed Virtual Company first-run sessions to Recipe Library as verified playbooks.
#
# Usage:
#   ./scripts/operator-save-vc-playbooks.sh
#   DRY_RUN=1 ./scripts/operator-save-vc-playbooks.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
DRY_RUN="${DRY_RUN:-0}"

declare -A TITLES=(
  ["marketing-ops"]="VC Marketing Ops · first simulate"
  ["lead-waterfall"]="VC Sales Ops · first simulate"
  ["rnd-dev"]="VC R&D · first simulate"
  ["finance-ops"]="VC Finance Ops · first simulate"
  ["digital-ops"]="VC Digital Ops · first simulate"
  ["product-ship"]="VC Product Ship · first simulate"
  ["life-os"]="VC Life OS · first simulate"
)

echo "== Save Virtual Company first-run playbooks to Recipe Library =="
echo "hive: ${HIVE_BASE} dry_run: ${DRY_RUN}"
echo

if ! docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  echo "Backend not running." >&2
  exit 1
fi

TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null)"
audit="$(curl -sk -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/virtual-company/readiness-audit")"

printf '%s' "$audit" | python3 -c "
import json, sys, urllib.request, urllib.error

audit = json.load(sys.stdin)
base, token, dry = sys.argv[1], sys.argv[2], sys.argv[3] == '1'
sessions = audit.get('checklist', {}).get('first_run', {}).get('sessions') or []
titles = {
    'marketing-ops': 'VC Marketing Ops · first simulate',
    'lead-waterfall': 'VC Sales Ops · first simulate',
    'rnd-dev': 'VC R&D · first simulate',
    'finance-ops': 'VC Finance Ops · first simulate',
    'digital-ops': 'VC Digital Ops · first simulate',
    'product-ship': 'VC Product Ship · first simulate',
    'life-os': 'VC Life OS · first simulate',
}
saved = skipped = failed = 0
for row in sessions:
    if row.get('status') != 'completed':
        print(f\"○ skip {row.get('template_id')} — status {row.get('status')}\")
        skipped += 1
        continue
    sid = row.get('session_id')
    tid = row.get('template_id', 'vc')
    name = titles.get(tid, f'VC {tid} · first simulate')
    body = json.dumps({
        'name': name,
        'description': f'Verified Virtual Company first-run simulate ({tid}).',
        'topic_tags': ['virtual-company', tid, 'simulate'],
        'mark_verified': True,
    }).encode()
    if dry:
        print(f'→ would save {tid} session {sid[:8]}… as {name!r}')
        saved += 1
        continue
    req = urllib.request.Request(
        f'{base}/api/v1/agents/sessions/{sid}/playbook',
        data=body,
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            out = json.loads(resp.read().decode())
        rid = str(out.get('recipe_id', '?'))
        print(f'✓ {tid} → recipe {rid[:8]}…')
        saved += 1
    except urllib.error.HTTPError as exc:
        if exc.code == 409:
            print(f'✓ {tid} — already in Recipe Library (409)')
            saved += 1
        else:
            print(f'✗ {tid} session {sid[:8]}… — HTTP Error {exc.code}: {exc.reason}')
            failed += 1
    except Exception as exc:
        print(f'✗ {tid} session {sid[:8]}… — {exc}')
        failed += 1
print()
print(f'Saved: {saved}, skipped: {skipped}, failed: {failed}')
sys.exit(1 if failed else 0)
" "${HIVE_BASE}" "${TOKEN}" "${DRY_RUN}"
