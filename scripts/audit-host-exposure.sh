#!/usr/bin/env bash
# Fail when data-plane ports are bound on all interfaces (0.0.0.0 / ::).
set -euo pipefail

FAIL=0
PORTS=(6379 5432 7474 7687 9090 3030 8000 3000)

echo "== Host exposure audit =="

for port in "${PORTS[@]}"; do
  if ss -ltn 2>/dev/null | grep -qE "0\.0\.0\.0:${port} |\[::\]:${port} "; then
    echo "FAIL: port ${port} listens on all interfaces (0.0.0.0 or ::)" >&2
    ss -ltnp 2>/dev/null | grep -E ":${port} " || true
    FAIL=1
  else
    echo "OK: port ${port} not on 0.0.0.0"
  fi
done

if command -v redis-cli >/dev/null 2>&1; then
  if redis-cli -h 127.0.0.1 ping 2>/dev/null | grep -q PONG; then
    echo "WARN: redis-cli PONG on 127.0.0.1 without auth — ensure requirepass or remove host bind" >&2
    FAIL=1
  else
    echo "OK: redis not accepting unauthenticated local ping"
  fi
fi

if docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep -E '0\.0\.0\.0:(6379|5432|7474|7687|9090|3030|8000|3000)->' | grep -v nginx; then
  echo "FAIL: Docker publishes data-plane port on 0.0.0.0 (see above)" >&2
  FAIL=1
else
  echo "OK: Docker data-plane ports not published on 0.0.0.0"
fi

if [[ "$FAIL" -ne 0 ]]; then
  echo "== Host exposure audit: FAILED ==" >&2
  exit 1
fi

echo "== Host exposure audit: OK =="
