#!/usr/bin/env bash
# End-to-end publish lane rollout — OAuth prep → Venice → simulate → live flip.
#
# Usage:
#   ./scripts/operator-publish-live-rollout.sh
#   RUN_SIMULATE=1 CONFIRM_LIVE=1 ./scripts/operator-publish-live-rollout.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Publish lane rollout — Meta OAuth · Venice · Live flip   ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo "docs: docs/OPERATOR_PUBLISH_LIVE_15MIN.md"
echo

echo "[1/6] OAuth env init + vendor prep"
MERGE=1 ./scripts/operator-oauth-env-init.sh || true
./scripts/operator-meta-oauth-prep.sh || true
echo

echo "[2/6] Publish lane status (before)"
./scripts/operator-publish-lane-status.sh || true
echo

echo "[3/6] Venice connector"
./scripts/operator-venice-connector-prep.sh || true
echo

echo "[4/6] Social OAuth status"
./scripts/operator-social-oauth-status.sh || true
echo

echo "[5/6] Simulate gate"
RUN_SIMULATE="${RUN_SIMULATE:-0}" ./scripts/operator-publish-simulate-gate.sh || {
  echo "WARN: simulate gate not fully green — fix OAuth/approve before live."
}
echo

echo "[6/6] Live enable"
CONFIRM_LIVE="${CONFIRM_LIVE:-0}" ./scripts/operator-publish-live-enable.sh || true

if [[ "${CONFIRM_LIVE:-0}" == "1" ]]; then
  echo
  echo "Redeploying after live flip…"
  POST_DEPLOY_HEALTH=1 ./scripts/deploy-prod.sh --env-file "${ENV_FILE:-.env.prod}"
  echo
  ./scripts/operator-publish-lane-status.sh || true
fi

echo
echo "== Manual steps (if OAuth keys still empty) =="
echo "  1. Edit .env.prod.oauth → OAUTH_META_CLIENT_ID + SECRET"
echo "  2. REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh"
echo "  3. Integrations → Marketplace → Install IG → Hub → Connect"
echo "  4. RUN_SIMULATE=1 CONFIRM_LIVE=1 $0"
