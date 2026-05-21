#!/usr/bin/env bash
# Close public access to data-plane ports on production hosts (Redis, Postgres, Neo4j, metrics).
set -euo pipefail

if ! command -v ufw >/dev/null 2>&1; then
  echo "harden-prod-firewall: ufw not installed — skip" >&2
  exit 0
fi

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "harden-prod-firewall: run as root (sudo $0)" >&2
  exit 1
fi

# Remove overly permissive Postgres rule if present.
while ufw status numbered | grep -qE '5432/tcp'; do
  rule_num="$(ufw status numbered | grep -E '5432/tcp' | head -1 | sed -n 's/^\[\([0-9]*\)\].*/\1/p')"
  [[ -n "$rule_num" ]] || break
  ufw --force delete "$rule_num"
done

for port in 6379 5432 7474 7687 9090 3030 8000 3000; do
  ufw deny "${port}/tcp" >/dev/null 2>&1 || true
done

ufw allow 22/tcp comment 'SSH' >/dev/null 2>&1 || true
ufw allow 80/tcp comment 'HTTP' >/dev/null 2>&1 || true
ufw allow 443/tcp comment 'HTTPS' >/dev/null 2>&1 || true

ufw --force enable >/dev/null 2>&1 || true
echo "harden-prod-firewall: data-plane ports denied; only 22/80/443 allowed inbound"
ufw status verbose | head -25
