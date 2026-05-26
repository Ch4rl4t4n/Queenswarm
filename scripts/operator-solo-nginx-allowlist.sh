#!/usr/bin/env bash
# Enable or disable nginx IP allowlist for solo operator (HTTPS only).
#
# Usage:
#   OPERATOR_IP=203.0.113.10 ./scripts/operator-solo-nginx-allowlist.sh enable
#   OPERATOR_IP=203.0.113.10,198.51.100.2 ./scripts/operator-solo-nginx-allowlist.sh enable
#   ./scripts/operator-solo-nginx-allowlist.sh disable
#   ./scripts/operator-solo-nginx-allowlist.sh status
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

INCLUDE="${ROOT}/deploy/nginx/includes/solo-operator-allowlist.conf"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-queenswarm_prod}"
NGINX_CONTAINER="${NGINX_CONTAINER:-${COMPOSE_PROJECT}-nginx-1}"
ACTION="${1:-status}"

write_disabled() {
  cat >"$INCLUDE" <<'EOF'
# Solo operator IP lock — DISABLED (public HTTPS).
# Enable: OPERATOR_IP=x.x.x.x ./scripts/operator-solo-nginx-allowlist.sh enable

# allow 203.0.113.10/32;
# deny all;
EOF
}

write_enabled() {
  local ips_csv="${OPERATOR_IP:-}"
  if [[ -z "${ips_csv// }" ]]; then
    echo "Set OPERATOR_IP (your public IPv4/IPv6, comma-separated for multiple)." >&2
    echo "Example: OPERATOR_IP=203.0.113.10 ./scripts/operator-solo-nginx-allowlist.sh enable" >&2
    exit 1
  fi
  {
    echo "# Solo operator IP lock — ENABLED $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    IFS=',' read -ra IPS <<<"$ips_csv"
    for raw in "${IPS[@]}"; do
      ip="${raw// /}"
      [[ -z "$ip" ]] && continue
      if [[ "$ip" == *:* ]]; then
        echo "allow ${ip};"
      else
        echo "allow ${ip}/32;"
      fi
    done
    echo "deny all;"
  } >"$INCLUDE"
}

reload_nginx() {
  if docker ps --format '{{.Names}}' | grep -qx "$NGINX_CONTAINER"; then
    docker exec "$NGINX_CONTAINER" nginx -t
    docker exec "$NGINX_CONTAINER" nginx -s reload
    echo "nginx reloaded ($NGINX_CONTAINER)"
  else
    echo "nginx container not running — redeploy to apply: ENV_FILE=.env.prod ./scripts/deploy-prod.sh" >&2
  fi
}

case "$ACTION" in
  enable)
    write_enabled
    reload_nginx
    echo "Allowlist ENABLED — only listed IPs reach https://queenswarm.love"
    cat "$INCLUDE"
    ;;
  disable)
    write_disabled
    reload_nginx
    echo "Allowlist DISABLED — public HTTPS restored"
    ;;
  status)
    echo "== Solo nginx allowlist =="
    echo "file: $INCLUDE"
    if grep -q '^deny all;' "$INCLUDE" 2>/dev/null; then
      echo "status: ENABLED"
    else
      echo "status: DISABLED"
    fi
    echo
    cat "$INCLUDE"
    ;;
  *)
    echo "Usage: OPERATOR_IP=x.x.x.x $0 {enable|disable|status}" >&2
    exit 1
    ;;
esac
