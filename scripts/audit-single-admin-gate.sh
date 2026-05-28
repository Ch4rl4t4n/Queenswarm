#!/usr/bin/env bash
# Guardrails for strict single-admin runtime support.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

check_line() {
  local file="$1" pattern="$2" hint="$3"
  if ! grep -q "${pattern}" "$file"; then
    echo "single-admin-gate: missing '${pattern}' in ${file} (${hint})" >&2
    exit 1
  fi
}

check_line ".env.prod.example" "SINGLE_ADMIN_MODE" "single-admin deployment toggle"
check_line ".env.prod.example" "NEXT_PUBLIC_SINGLE_ADMIN_MODE" "frontend single-admin shell toggle"

echo "single-admin-gate: PASS"

