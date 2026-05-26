#!/usr/bin/env bash
# Enable all solo optional modules: env keys + platform feature matrix (environment column).
#
# Usage:
#   ./scripts/operator-solo-enable-modules.sh              # apply + redeploy celery/backend
#   APPLY=0 ./scripts/operator-solo-enable-modules.sh      # dry-run (print only)
#   ENV_FILE=.env.prod ./scripts/operator-solo-enable-modules.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-queenswarm_prod}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-${COMPOSE_PROJECT}-backend-1}"
APPLY="${APPLY:-1}"

upsert_kv() {
  local file="$1" key="$2" value="$3"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '\n%s=%s\n' "$key" "$value" >>"$file"
  fi
}

load_kv() {
  local file="$1" key="$2"
  local line val
  [[ -f "$file" ]] || return 1
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    if [[ "$line" =~ ^${key}= ]]; then
      val="${line#*=}"
      val="${val%$'\r'}"
      if [[ "$val" == \"*\" ]]; then val="${val:1:-1}"; fi
      printf '%s' "$val"
      return 0
    fi
  done <"$file"
  return 1
}

echo "== Solo optional modules enable =="
echo "env: ${ENV_FILE}"
echo "APPLY=${APPLY}"
echo

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing ${ENV_FILE}" >&2
  exit 1
fi

# Env keys that back optional modules (platform matrix still required in solo mode).
ENV_TO_ENABLE=(
  "FORAGER_INTELLIGENCE_LOOP_ENABLED=true"
  "SIMULATIONS_ENABLED=true"
  "LSP_MCP_BRIDGE_ENABLED=true"
  "RUBRIC_TEMPLATES_ENABLED=true"
  "EPISODIC_MEMORY_ENABLED=true"
)

# Slack trainer only when signing secret already configured.
slack_secret="$(load_kv "$ENV_FILE" SLACK_HARNESS_TRAINER_SIGNING_SECRET || true)"
if [[ -n "${slack_secret// }" ]]; then
  ENV_TO_ENABLE+=("SLACK_HARNESS_TRAINER_ENABLED=true")
  echo "Slack harness trainer: signing secret present → will enable"
else
  echo "Slack harness trainer: no SLACK_HARNESS_TRAINER_SIGNING_SECRET → UI only (platform matrix)"
fi
echo

for pair in "${ENV_TO_ENABLE[@]}"; do
  key="${pair%%=*}"
  value="${pair#*=}"
  if [[ "$APPLY" == "1" ]]; then
    upsert_kv "$ENV_FILE" "$key" "$value"
    echo "  ✓ ${key}=${value}"
  else
    echo "  would set ${key}=${value}"
  fi
done

echo
echo "[Platform matrix — environment column]"
if [[ "$APPLY" == "1" ]]; then
  if ! docker ps --format '{{.Names}}' | grep -qx "$BACKEND_CONTAINER"; then
    echo "Backend container not running: ${BACKEND_CONTAINER}" >&2
    exit 1
  fi
  docker cp "${ROOT}/backend/scripts/apply_solo_platform_modules.py" \
    "${BACKEND_CONTAINER}:/app/scripts/apply_solo_platform_modules.py"
  docker exec "$BACKEND_CONTAINER" python scripts/apply_solo_platform_modules.py
else
  echo "  would run: docker exec ${BACKEND_CONTAINER} python scripts/apply_solo_platform_modules.py"
fi

if [[ "$APPLY" != "1" ]]; then
  echo
  echo "Dry run complete (APPLY=0)."
  exit 0
fi

echo
echo "Redeploying backend + celery (env + beat schedule) …"
docker compose -p "$COMPOSE_PROJECT" \
  -f docker-compose.base.yml \
  -f docker-compose.prod.yml \
  --env-file "$ENV_FILE" \
  up -d --force-recreate backend celery-worker celery-beat

echo
echo "Done. Hard-refresh dashboard (Ctrl+Shift+R)."
echo "Verify: Settings → Platform → stĺpec Prostredie — optional modules ON."
echo "Audit:  ./scripts/operator-solo-readiness-audit.sh"
