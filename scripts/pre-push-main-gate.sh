#!/usr/bin/env bash
# Block push to main when local CI would fail on GitHub — prevents red CI email spam.
#
# Install: ./scripts/install-git-hooks.sh
# Bypass (emergency only): SKIP_MAIN_CI_GATE=1 git push origin main
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

remote="${1:-}"
url="${2:-}"
branch="${3:-}"

# Only gate pushes that update refs/heads/main on a remote.
if [[ "${remote}" != "origin" && "${remote}" != *"github.com"* ]]; then
  exit 0
fi
if [[ "${branch}" != "refs/heads/main" && "${branch}" != "main" ]]; then
  exit 0
fi
if [[ "${SKIP_MAIN_CI_GATE:-}" == "1" ]]; then
  echo "pre-push: SKIP_MAIN_CI_GATE=1 — CI gate bypassed (use only for emergencies)."
  exit 0
fi

echo "pre-push: main → remote — running full CI parity (./scripts/ci-local.sh all)…"
chmod +x "${ROOT}/scripts/ci-local.sh"
"${ROOT}/scripts/ci-local.sh" all
echo "pre-push: CI parity passed — push allowed."
