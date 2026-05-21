#!/usr/bin/env bash
# Print a Hetzner abuse reply draft + run host exposure audit evidence.
#
# Usage:
#   ./scripts/hetzner-abuse-reply.sh
#   ABUSE_ID=11B0286:23 ./scripts/hetzner-abuse-reply.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ABUSE_ID="${ABUSE_ID:-11B0286:23}"
DOMAIN="${DOMAIN:-queenswarm.love}"
TIMESTAMP="$(date -u +"%Y-%m-%d %H:%M:%S UTC")"

echo "== Hetzner abuse reply draft =="
echo "To: abuse@hetzner.com"
echo "Subject: Re: AbuseID ${ABUSE_ID} — remediation completed"
echo
cat <<EOF
Dear Hetzner Abuse Team,

We acknowledge AbuseID ${ABUSE_ID} regarding an open Redis service on our server.

Root cause: Docker Compose published Redis (and other data-plane services) on 0.0.0.0 without authentication.

Remediation completed on ${TIMESTAMP}:
- Removed public port bindings for Redis, PostgreSQL, Neo4j, Prometheus, Grafana, backend, and frontend in production overlay
- Enabled Redis requirepass and synchronized REDIS_URL / Celery broker URLs
- Hardened host firewall (UFW) to DENY inbound data-plane ports (6379, 5432, 7474, 7687, 9090, 3030, 8000, 3000)
- Only nginx remains publicly accessible on ports 80/443 for ${DOMAIN}

Evidence: automated host exposure audit output attached below (exit 0 required).

We confirm the issue is resolved and will prevent recurrence via pre-deploy audit gates.

Best regards,
Queenswarm Operations
EOF

echo
echo "== Host exposure audit evidence (${TIMESTAMP}) =="
"${ROOT}/scripts/audit-host-exposure.sh"

echo
echo "== Next step =="
echo "Copy the reply above into your mail client and send to abuse@hetzner.com with AbuseID ${ABUSE_ID}."
