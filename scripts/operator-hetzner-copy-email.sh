#!/usr/bin/env bash
# Refresh Hetzner abuse reply + print mail-client copy-paste block.
#
# Usage:
#   ./scripts/operator-hetzner-copy-email.sh
#   ./scripts/operator-hetzner-copy-email.sh --no-refresh   # use latest draft only
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ABUSE_ID="${ABUSE_ID:-11B0286:23}"
REFRESH=1
if [[ "${1:-}" == "--no-refresh" ]]; then
  REFRESH=0
fi

if [[ "$REFRESH" -eq 1 ]]; then
  echo "Refreshing draft with latest host exposure audit…"
  ./scripts/hetzner-abuse-reply.sh >/dev/null
fi

LATEST="$(ls -1 "${ROOT}/reports/hetzner/hetzner-reply-"*.txt 2>/dev/null | tail -1 || true)"
if [[ -z "$LATEST" ]]; then
  echo "No hetzner reply file — run ./scripts/hetzner-abuse-reply.sh first" >&2
  exit 1
fi

SUBJECT="Re: AbuseID ${ABUSE_ID} — remediation completed"
TO="abuse@hetzner.com"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Hetzner abuse email — copy-paste                        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo
echo "To:      ${TO}"
echo "Subject: ${SUBJECT}"
echo "Body:    (below — include audit evidence at bottom)"
echo "File:    ${LATEST}"
echo
echo "─────────────────── BEGIN EMAIL BODY ───────────────────"
cat "$LATEST"
echo "─────────────────── END EMAIL BODY ─────────────────────"
echo
echo "After sending:"
echo "  1. ./scripts/operator-mark-hetzner-sent.sh"
echo "  2. Re-run: ./scripts/operator-pending-status.sh"
echo
echo "Reference: docs/OPERATOR_HETZNER_SEND.md"
