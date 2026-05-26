#!/usr/bin/env bash
# One-shot social OAuth prep for publish lane — env init, vendor guides, status probe.
#
# Usage:
#   ./scripts/operator-social-oauth-prep-all.sh
#   MERGE=1 ./scripts/operator-social-oauth-prep-all.sh   # merge missing keys into .env.prod.oauth
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MERGE="${MERGE:-1}"
export MERGE

echo "╔══════════════════════════════════════════════════╗"
echo "║  Social OAuth prep (publish lane)                 ║"
echo "╚══════════════════════════════════════════════════╝"
echo

./scripts/operator-oauth-env-init.sh
echo
./scripts/operator-oauth-env-prep.sh || true
echo
for script in \
  operator-meta-oauth-prep.sh \
  operator-x-oauth-prep.sh \
  operator-tiktok-oauth-prep.sh; do
  echo "--- ${script} ---"
  "./scripts/${script}" 2>&1 | tail -8
  echo
done

./scripts/operator-social-oauth-status.sh
echo
echo "When keys are filled:"
echo "  REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh"
echo "  Marketplace → Install → Connector Hub → Connect"
echo "  RUN_SIMULATE=1 ./scripts/operator-publish-simulate-gate.sh"
