#!/usr/bin/env bash
# Hetzner abuse reply — print send instructions + file path (no email sent).
#
# Usage:
#   ./scripts/operator-hetzner-send-prep.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ABUSE_ID="${ABUSE_ID:-11B0286:23}"
LATEST="$(ls -1 "${ROOT}/reports/hetzner/hetzner-reply-"*.txt 2>/dev/null | tail -1 || true)"

if [[ -z "$LATEST" ]]; then
  echo "No hetzner reply file — run ./scripts/hetzner-abuse-reply.sh first" >&2
  exit 1
fi

echo "== Hetzner abuse send prep =="
echo
echo "To:      abuse@hetzner.com"
echo "Subject: Re: AbuseID ${ABUSE_ID} — remediation completed"
echo "Attach:  ${LATEST}"
echo
echo "--- body preview (first 20 lines) ---"
head -20 "$LATEST"
echo "---"
echo
echo "Action: copy ${LATEST} into your mail client and send."
echo "After sent, note timestamp in ops log."
