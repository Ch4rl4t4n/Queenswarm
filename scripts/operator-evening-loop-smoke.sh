#!/usr/bin/env bash
# Evening operator loop smoke — Dump & Sleep → overnight report → episodic memory.
#
# Simulates the recommended nightly workflow on production.
#
# Usage:
#   ./scripts/operator-evening-loop-smoke.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
STAMP="$(date -u +%Y%m%d-%H%M%S)"

resolve_jwt() {
  docker exec "$BACKEND" python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n'
}

echo "== Evening loop smoke (${STAMP}) =="
echo "hive: ${HIVE_BASE}"
echo

TOKEN="$(resolve_jwt)"
[[ -n "${TOKEN// }" ]] || { echo "JWT missing" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cat > "${TMP}/priorities.md" <<EOF
# Večerný dump — ${STAMP}

## Zajtra
- Full app UI walkthrough audit (krok za krokom)
- Skontrolovať Marketing ops routine output v Notion simulate
- Review Life OS morning briefing

## Stalled
- Legacy migration je stalled — čaká na schválenie operátora
- n8n integrácia on hold — native-first automation stačí

## Nápady
- Slack webhook pre Alertmanager
- Episodic memory export do Obsidian
EOF

cat > "${TMP}/notes.txt" <<EOF
Quick capture: VC readiness 100%, 8 routines active.
Grok free_first routing OK. Telegram notifications working.
EOF

echo "[1/5] Submit Dump & Sleep batch (2 files + voice note)"
RESP="$(curl -sk -X POST "${HIVE_BASE}/api/v1/dump-sleep/batches" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "files=@${TMP}/priorities.md;type=text/markdown" \
  -F "files=@${TMP}/notes.txt;type=text/plain" \
  -F "voice_note=Večerný hlasový zápis: zajtra full app audit a review stalled projektov.")"
echo "$RESP" | python3 -m json.tool | head -15
BATCH_ID="$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || true)"
[[ -n "${BATCH_ID// }" ]] || { echo "Batch create failed" >&2; exit 1; }
echo

echo "[2/5] Poll batch until completed (max 60s)"
for i in $(seq 1 15); do
  sleep 4
  BODY="$(curl -sk -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/dump-sleep/batches/${BATCH_ID}")"
  ST="$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''), d.get('items_ingested',0), d.get('stalled_signals',0), d.get('pollen_earned',0))" 2>/dev/null || echo "?")"
  echo "  poll ${i}: ${ST}"
  if echo "$ST" | grep -qE '^completed'; then
    echo "$BODY" | python3 -c "
import json,sys
d=json.load(sys.stdin)
b=d.get('briefing_md','')
print('--- briefing preview ---')
print(b[:600])
print('...' if len(b)>600 else '')
"
    break
  fi
  if echo "$ST" | grep -qE '^failed'; then
    echo "$BODY" | python3 -m json.tool
    exit 1
  fi
done
echo

echo "[3/5] Overnight report"
curl -sk -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/dump-sleep/overnight-report" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('available:', d.get('available'))
b=d.get('batch') or {}
if b:
    print('batch_id:', b.get('id','')[:8]+'…')
    print('items_ingested:', b.get('items_ingested'))
    print('stalled_signals:', b.get('stalled_signals'))
    print('pollen_earned:', b.get('pollen_earned'))
"
echo

echo "[4/5] Episodic memory (dump_sleep count)"
curl -sk -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/memory/episodic/summary" | python3 -m json.tool
echo

echo "[5/5] Life OS routine next run"
curl -sk -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/agents/routines" | python3 -c "
import json,sys
for r in json.load(sys.stdin):
    if r.get('context_payload',{}).get('wizard_template')=='life-os':
        print('routine:', r['name'])
        print('cron:', r.get('cron_expr'))
        print('next_run:', r.get('next_run_at'))
        break
"

echo
echo "== Evening loop smoke: OK =="
echo "UI: Ballroom → Dump & Sleep | Knowledge → Dreaming card | Episodic Memory"
