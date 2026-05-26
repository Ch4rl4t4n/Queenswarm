#!/usr/bin/env bash
# Agent OS P8 audit — autonomy layer (cross-swarm, imitation, behavioral, analysis, trade→content).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Agent OS P8 Audit ==="

for f in \
  backend/app/application/services/agent_os.py \
  backend/app/application/services/analysis_swarm.py \
  backend/app/application/services/trading_risk_validator.py \
  backend/app/application/services/trade_to_content.py \
  backend/app/application/services/cross_swarm_knowledge.py \
  backend/app/application/services/imitation_v2.py \
  backend/app/application/services/dreaming_behavioral_proposals.py \
  backend/app/presentation/api/routers/agent_os.py \
  backend/app/worker/trading_overnight_tasks.py \
  frontend/components/hive/agent-os-panel.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "agent_os_router" backend/app/presentation/api/v1.py; then
  pass "router registered in v1"
else
  fail "agent_os router not in v1"
fi

if grep -q "polymarket-trading" frontend/lib/swarm-wizard-templates.ts; then
  pass "Polymarket Trading swarm template"
else
  fail "missing trading swarm template"
fi

if grep -q "content-flywheel-v2" frontend/lib/swarm-wizard-templates.ts; then
  pass "Content Flywheel 2.0 template"
else
  fail "missing content flywheel v2"
fi

if grep -q "validate_trading_risk" backend/app/application/services/paper_trading_service.py; then
  pass "risk validator wired in paper trading"
else
  fail "risk validator not wired"
fi

if grep -q "create_publish_draft_from_paper_fill" backend/app/application/services/paper_trading_service.py; then
  pass "trade→content wired on paper fill"
else
  fail "trade→content not wired"
fi

if grep -q "LazyAgentOsPanel" frontend/components/hive/solo-operator-trio-panel.tsx; then
  pass "Agent OS panel in harness"
else
  fail "Agent OS panel not wired"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest \
    tests/test_trading_risk_validator_unit.py \
    tests/test_analysis_swarm_unit.py \
    tests/test_dreaming_behavioral_proposals_unit.py \
    tests/test_agent_os_unit.py \
    -q --no-cov); then
    pass "pytest agent os P8"
  else
    fail "pytest agent os P8"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "AGENT OS P8 AUDIT: PASS"
  exit 0
fi
echo "AGENT OS P8 AUDIT: FAIL (${FAIL})"
exit 1
