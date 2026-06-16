#!/usr/bin/env bash
# Operator release gate — solo trio + publish pack + core health.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=1; }

echo "=== Operator Release Gate (solo) ==="

for script in \
  audit-solo-trio-gate.sh \
  audit-publish-pack-gate.sh \
  audit-publish-queue-gate.sh \
  audit-morning-publish-pipeline-gate.sh \
  audit-social-publish-gate.sh \
  audit-publish-lane-hardening-gate.sh \
  audit-publish-lane-complete-gate.sh \
  audit-trading-cockpit-gate.sh \
  audit-operator-loop-gate.sh \
  audit-publish-performance-gate.sh \
  audit-agent-os-p8-gate.sh \
  audit-roadmap-p9-gate.sh \
  audit-research-bee-gate.sh \
  audit-pattern-router-agency-gate.sh \
  audit-micro-saas-factory-gate.sh \
  audit-live-lane-gate.sh \
  audit-operator-hub-settings-gate.sh \
  audit-operator-control-plane-gate.sh \
  audit-analytics-workspace-gate.sh \
  operator-automation-ladder-audit.sh \
  audit-harness-self-improve-gate.sh \
  audit-phase-e-publish-gate.sh \
  operator-publish-simulate-gate.sh \
  operator-live-publish-gate.sh \
  audit-prediction-markets-gate.sh \
  audit-host-exposure.sh; do
  echo ""
  echo "--- $script ---"
  if [[ "$script" == "audit-operator-hub-settings-gate.sh" ]]; then
    if E2E_OPERATOR_HUB=1 ./scripts/"$script"; then
      pass "$script (with E2E)"
    else
      fail "$script"
    fi
  elif [[ "$script" == "audit-harness-self-improve-gate.sh" ]]; then
    if E2E_HARNESS_SELF_IMPROVE=1 ./scripts/"$script"; then
      pass "$script (with E2E)"
    else
      fail "$script"
    fi
  elif ./scripts/"$script"; then
    pass "$script"
  else
    fail "$script"
  fi
done

echo ""
if [[ -f ./scripts/operator-pending-status.sh ]]; then
  ./scripts/operator-pending-status.sh | head -30 || true
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "OPERATOR RELEASE GATE: PASS"
  echo "Manual: Load Brain Pack starter · Publish onboarding · OAuth → Simulate → live"
  exit 0
fi
echo "OPERATOR RELEASE GATE: FAIL"
exit 1
