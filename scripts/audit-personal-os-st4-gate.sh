#!/usr/bin/env bash
# ST4 — Config adoption gate (JA2 curated memory + CE provision + OP6 hygiene).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS ST4 Gate (JA2 · CE · OP5/6) ==="

if [[ -x "${ROOT}/scripts/operator-community-engagement-provision.sh" ]]; then
  pass "CE provision script present"
else
  fail "missing operator-community-engagement-provision.sh"
fi

if [[ -f docs/JARVIS_PERSONAL_ADVISOR_SETUP.md ]]; then
  pass "JAR setup doc"
else
  fail "missing JARVIS setup doc"
fi

if docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  docker cp "$ROOT/backend/scripts/operator_st4_task_hygiene.py" "$BACKEND:/app/scripts/operator_st4_task_hygiene.py" 2>/dev/null || true
  HYGIENE="$(docker exec "$BACKEND" python scripts/operator_st4_task_hygiene.py 2>/dev/null || echo '{}')"
  MISSION_CHARS="$(docker exec "$BACKEND" python -c "
import asyncio, json
from sqlalchemy import select
from app.core.database import async_session
from app.application.services.curated_memory_service import CuratedFileKind, CuratedMemoryService
from app.infrastructure.persistence.models import load_all_models
from app.infrastructure.persistence.models.tenant import Tenant
load_all_models()
async def main():
    async with async_session() as s:
        rows = list((await s.scalars(select(Tenant).order_by(Tenant.created_at))).all())
        tenant = rows[-1]
        bundle = await CuratedMemoryService(db=s).get_bundle(tenant.id)
        print(len(bundle.get(CuratedFileKind.MISSION, '') or ''))
asyncio.run(main())
" 2>/dev/null || echo 0)"
  if [[ "${MISSION_CHARS:-0}" -ge 200 ]]; then
    pass "JA2 MISSION curated (${MISSION_CHARS} chars)"
  else
    fail "JA2 MISSION empty — run ./scripts/operator-hive-policy-seed.sh"
  fi
  OP6_FOUND="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(len(d.get('op6_found',[])))" "$HYGIENE")"
  if [[ "${OP6_FOUND:-0}" -eq 0 ]]; then
    pass "OP6 mistaken Life OS task absent"
  else
    fail "OP6 task still active — run operator_st4_task_hygiene.py --apply"
  fi
else
  fail "backend container not running ($BACKEND)"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "ST4 GATE: PASS"
  exit 0
fi
echo "ST4 GATE: FAIL ($FAIL)"
exit 1
