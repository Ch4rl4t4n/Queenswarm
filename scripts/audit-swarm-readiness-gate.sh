#!/usr/bin/env bash
# Swarm readiness gate — env flags, skill files, connector health hints.
#
# Usage:
#   ./scripts/audit-swarm-readiness-gate.sh
#   ENV_FILE=.env.prod ./scripts/audit-swarm-readiness-gate.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/.env.prod}"
SKILLS_DIR="${ROOT}/backend/app/skills"
FAIL=0

pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=1; }
warn() { echo "  WARN $*"; }

load_kv() {
  local key="$1"
  local line val
  [[ -f "$ENV_FILE" ]] || return 1
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    if [[ "$line" =~ ^${key}= ]]; then
      val="${line#*=}"
      val="${val%$'\r'}"
      val="${val#\"}"
      val="${val%\"}"
      printf '%s' "$val"
      return 0
    fi
  done <"$ENV_FILE"
  return 1
}

is_truthy() {
  local raw="${1:-}"
  local norm
  norm="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  [[ "$norm" == "1" || "$norm" == "true" || "$norm" == "yes" || "$norm" == "on" ]]
}

echo "=== Swarm Readiness Gate ==="
echo "ENV_FILE=${ENV_FILE}"

echo ""
echo "--- priority env flags ---"
REQUIRED_FLAGS=(
  AGENT_OS_ENABLED
  HIVE_MIND_ENABLED
  IMITATION_V2_ENABLED
  EXECUTION_STUDIO_ENABLED
  RESEARCH_BEE_ENABLED
  HIVE_INNOVATION_LAB_ENABLED
  QUEEN_MAINTAINER_ENABLED
  SOCIAL_PUBLISH_ENABLED
  PAPER_TRADING_ENABLED
)
for flag in "${REQUIRED_FLAGS[@]}"; do
  val="$(load_kv "$flag" 2>/dev/null || true)"
  if is_truthy "$val"; then
    pass "${flag}=enabled"
  else
    warn "${flag} not enabled (recommended for full swarm)"
  fi
done

LIVE_PUBLISH="$(load_kv SOCIAL_PUBLISH_LIVE_ENABLED 2>/dev/null || true)"
if is_truthy "$LIVE_PUBLISH"; then
  warn "SOCIAL_PUBLISH_LIVE_ENABLED=true — ensure operator-approval-gate skill active"
else
  pass "SOCIAL_PUBLISH_LIVE simulate-first default"
fi

echo ""
echo "--- Week-1 backend skills ---"
WEEK1_SKILLS=(
  operator-approval-gate
  research-to-pr-proposal
  marketing-campaign-playbook
  trading-paper-discipline
  multi-tenant-content-calendar
  competitor-scrape-analyze
  eshop-ops-research
  real-money-risk-gate
  social-simulate-first
  skill-authoring-template
)
WEEK2_SKILLS=(
  stripe-checkout-webhooks
  seo-audit-playbook
  ga4-analytics-playbook
  email-drip-sequences
  business-analytics-playbook
)
for slug in "${WEEK1_SKILLS[@]}" "${WEEK2_SKILLS[@]}"; do
  if [[ -f "${SKILLS_DIR}/${slug}.md" ]]; then
    if grep -q "^name: ${slug}" "${SKILLS_DIR}/${slug}.md" 2>/dev/null; then
      pass "skill ${slug}.md (agentskills name field)"
    else
      warn "skill ${slug}.md missing name: frontmatter"
    fi
  else
    fail "missing skill ${slug}.md"
  fi
done

echo ""
echo "--- Phase 3 ecommerce connectors ---"
for tid in shopify_admin_api stripe_rest_api; do
  if grep -q "template_id=\"${tid}\"" "${ROOT}/backend/app/infrastructure/connectors/phase3/catalog.py" 2>/dev/null; then
    pass "phase3 ${tid}"
  else
    fail "missing phase3 ${tid}"
  fi
done

echo ""
echo "--- skill library unit smoke ---"
if [[ -x "${ROOT}/backend/venv/bin/python" ]]; then
  PY="${ROOT}/backend/venv/bin/python"
elif docker ps --format '{{.Names}}' 2>/dev/null | grep -q 'queenswarm_prod-backend-1'; then
  if docker exec queenswarm_prod-backend-1 python -m pytest tests/test_swarm_readiness_skills_unit.py -q --no-cov 2>/dev/null; then
    pass "SkillLibrary smoke (container pytest)"
    PY=""
  else
    PY=""
    fail "SkillLibrary smoke (container pytest)"
  fi
else
  PY="python3"
fi
if [[ -n "${PY:-}" ]]; then
  if (cd "${ROOT}/backend" && "$PY" -c "
from app.application.services.supervisor.skills import SkillLibrary
lib = SkillLibrary()
slugs = lib.list_available_slugs()
assert 'operator-approval-gate' in slugs
assert lib.load('marketing-campaign-playbook') is not None
picked = lib.select_for_task(role='researcher', goal='competitor scrape marketing campaign')
assert 'competitor-scrape-analyze' in picked or 'marketing-campaign-playbook' in picked
print(f'loaded {len(slugs)} skills')
"); then
    pass "SkillLibrary smoke"
  else
    fail "SkillLibrary smoke"
  fi
fi

echo ""
echo "--- production health (optional) ---"
if [[ "${SKIP_HEALTH_CHECK:-0}" != "1" ]] && [[ -f "$ENV_FILE" ]]; then
  if PRD_ENV_FILE="$ENV_FILE" "${ROOT}/scripts/health-check.sh" >/dev/null 2>&1; then
    pass "health-check.sh"
  else
    warn "health-check failed or unreachable"
  fi
else
  echo "  skip health"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "SWARM READINESS GATE: PASS"
  exit 0
fi
echo "SWARM READINESS GATE: FAIL"
exit 1
