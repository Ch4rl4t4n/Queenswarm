#!/usr/bin/env bash
# Pre-production health: deterministic BE/FE checks with optional e2e and strict security.
#
# Optional:
#   RUN_E2E=1            -> run Playwright smoke (default: 0)
#   RUN_SECURITY_GATES=1 -> run security gates at end (default: 1)
#   SECURITY_STRICT=1    -> strict dependency enforcement for security gates
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Pre-production health ==="
echo "== Host memory (Linux) =="
if [[ -r /proc/meminfo ]]; then
  awk '/MemTotal|MemAvailable/{print}' /proc/meminfo
  avail_kb=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
  # Warn below ~512 MiB available (tunable heuristic for small VMs)
  if [[ "${avail_kb}" -lt 524288 ]]; then
    echo "WARN: MemAvailable < 512 MiB — risk of OOM under parallel Playwright; prefer low_ram poll profile or fewer workers."
  fi
else
  echo "(skip: /proc/meminfo not readable)"
fi

echo "== Backend pytest full regression =="
cd "${ROOT}/backend"
./venv/bin/pytest --no-cov

echo "== Frontend typecheck + Vitest =="
cd "${ROOT}/frontend"
npm run typecheck
npm run test -- --run

if [[ "${RUN_E2E:-0}" == "1" ]]; then
  echo "== Playwright smoke =="
  CI=true npm run test:e2e
fi

if [[ "${RUN_SECURITY_GATES:-1}" == "1" ]]; then
  echo "== Security gates =="
  cd "${ROOT}"
  SECURITY_STRICT="${SECURITY_STRICT:-1}" ./scripts/security-gates.sh
fi

echo "=== pre-production-health-check: OK ==="
