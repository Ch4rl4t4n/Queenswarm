#!/usr/bin/env bash
# Run all operator P0 prep scripts in order (read-only except none mutate prod).
#
# Usage:
#   ./scripts/operator-p0-prep-all.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Queenswarm Operator P0 — prep all                       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo

scripts=(
  "operator-launch-checklist.sh"
  "operator-stripe-dashboard-checklist.sh"
  "operator-stripe-prep.sh"
  "operator-hetzner-send-prep.sh"
  "operator-hetzner-copy-email.sh"
  "operator-resolve-tenant-id.sh"
  "operator-github-webhook-prep.sh"
  "operator-harness-env-prep.sh"
)

exit_code=0
for script in "${scripts[@]}"; do
  echo "──────────────────────────────────────────────────────────"
  echo "▶ ./scripts/${script}"
  echo "──────────────────────────────────────────────────────────"
  if [[ -x "./scripts/${script}" ]]; then
    set +e
    "./scripts/${script}"
    rc=$?
    set -e
    case "${script}:${rc}" in
      operator-launch-checklist.sh:2) echo "(exit 2 = Stripe keys pending — expected)" ;;
      operator-stripe-prep.sh:1) echo "(exit 1 = Stripe keys missing — expected)" ;;
      operator-stripe-dashboard-checklist.sh:1) echo "(exit 1 = Stripe Dashboard steps pending — expected)" ;;
      operator-github-webhook-prep.sh:1) echo "(exit 1 = harness webhook keys missing — expected)" ;;
      operator-harness-env-prep.sh:1) echo "(exit 1 = optional harness keys missing — expected)" ;;
      *:0) ;;
      *) exit_code=$rc ;;
    esac
  else
    echo "Missing or not executable: ./scripts/${script}" >&2
    exit_code=1
  fi
  echo
done

echo "== Operator P0 prep all finished (exit=${exit_code}) =="
echo "Next: add Stripe keys → ./scripts/operator-p0-close.sh"
exit "$exit_code"
