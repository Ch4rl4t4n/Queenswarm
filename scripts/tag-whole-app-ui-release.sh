#!/usr/bin/env bash
# Whole-App UI Reorder — annotated release tag after extended gate PASS.
#
# Env:
#   WHOLE_APP_UI_RELEASE_TAG   — default v2026.05-whole-app-ui (SSOT in hive-release-gate-spec.ts)
#   WHOLE_APP_TAG_ALLOW_DIRTY=1 — allow uncommitted changes (not recommended for prod tags)
#   SKIP_EXTENDED_GATE=1       — skip gate (emergency only)
#   PLAYWRIGHT_WORKERS=2
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAG="${WHOLE_APP_UI_RELEASE_TAG:-v2026.05-whole-app-ui}"
ALLOW_DIRTY="${WHOLE_APP_TAG_ALLOW_DIRTY:-0}"
SKIP_GATE="${SKIP_EXTENDED_GATE:-0}"

cd "$ROOT"

echo "=== Whole-App UI Release Tag ==="
echo "Target tag: ${TAG}"

if [[ "$ALLOW_DIRTY" != "1" ]]; then
  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "FAIL: working tree has uncommitted changes." >&2
    echo "Commit first, or set WHOLE_APP_TAG_ALLOW_DIRTY=1 to override." >&2
    exit 1
  fi
  if [[ -n "$(git status --porcelain --untracked-files=normal)" ]]; then
    echo "FAIL: untracked files present." >&2
    echo "Commit or clean untracked files before tagging." >&2
    exit 1
  fi
fi

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "FAIL: tag ${TAG} already exists at $(git rev-parse "$TAG")." >&2
  echo "Delete locally with: git tag -d ${TAG}" >&2
  exit 1
fi

echo ""
echo "--- verify release gate SSOT ---"
if ! (cd "$ROOT/frontend" && npm run test -- --run lib/hive-release-gate-spec.test.ts); then
  echo "FAIL: hive-release-gate-spec unit tests" >&2
  exit 1
fi

if [[ "$SKIP_GATE" != "1" ]]; then
  echo ""
  echo "--- extended release gate (required before tag) ---"
  WHOLE_APP_EXTENDED_GATE=1 PLAYWRIGHT_WORKERS="${PLAYWRIGHT_WORKERS:-2}" SKIP_HEALTH_CHECK=1 \
    "$ROOT/scripts/whole-app-ui-release-gate.sh"
else
  echo "SKIP: extended gate (SKIP_EXTENDED_GATE=1)"
fi

COMMIT="$(git rev-parse --short HEAD)"
MESSAGE="$(cat <<EOF
Whole-App UI Reorder shippable release (${TAG})

Gate: 2026.05-v5
Phases: 1–19 complete (IA, shell, settings, modals, cross-links, execution lane, workflows shell)
Runbook: docs/WHOLE_APP_UI_RELEASE_RUNBOOK.md
Commit: ${COMMIT}
EOF
)"

git tag -a "$TAG" -m "$MESSAGE"

echo ""
echo "TAG CREATED: ${TAG} @ ${COMMIT}"
echo "Push with: git push origin ${TAG}"
