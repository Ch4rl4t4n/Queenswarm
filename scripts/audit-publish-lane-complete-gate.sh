#!/usr/bin/env bash
# Master publish lane gate — A→H code-complete verification (no operator OAuth required).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "╔══════════════════════════════════════════════════╗"
echo "║  Publish Lane Complete Gate (A → H)              ║"
echo "╚══════════════════════════════════════════════════╝"
echo

for script in \
  audit-publish-pack-gate.sh \
  audit-publish-queue-gate.sh \
  audit-social-publish-gate.sh \
  audit-morning-publish-pipeline-gate.sh \
  audit-phase-e-publish-gate.sh \
  audit-publish-lane-hardening-gate.sh; do
  echo "--- ${script} ---"
  if ./scripts/"${script}"; then
    pass "${script}"
  else
    fail "${script}"
  fi
  echo
done

echo "--- backend publish lane pytest bundle ---"
if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest \
    tests/test_publish_pack_unit.py \
    tests/test_publish_queue_unit.py \
    tests/test_social_publish_unit.py \
    tests/test_social_publish_trusted_auto_unit.py \
    tests/test_social_publish_rate_limit_unit.py \
    tests/test_publish_media_unit.py \
    tests/test_publish_audit_unit.py \
    tests/test_tiktok_publish_status_unit.py \
    tests/test_publish_pack_media_hook_unit.py \
    tests/test_publish_pack_video_hook_unit.py \
    tests/test_publish_operator_onboarding_unit.py \
    tests/test_publish_operator_onboarding_admin_unit.py \
    tests/test_phase_e_publish_unit.py \
    -q --no-cov); then
    pass "publish lane pytest bundle"
  else
    fail "publish lane pytest bundle"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "PUBLISH LANE COMPLETE: PASS"
  exit 0
fi
echo "PUBLISH LANE COMPLETE: FAIL (${FAIL} sub-gate(s))"
exit 1
