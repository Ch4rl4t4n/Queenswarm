#!/usr/bin/env bash
# Print tenant UUID(s) for harness env (QUEEN_MAINTAINER_POST_MERGE_TENANT_ID).
# Read-only — queries prod Postgres via docker; no secrets printed.
#
# Usage:
#   ./scripts/operator-resolve-tenant-id.sh
#   ./scripts/operator-resolve-tenant-id.sh --primary
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE_PROJECT="${COMPOSE_PROJECT:-queenswarm_prod}"
PG_CONTAINER="${PG_CONTAINER:-${COMPOSE_PROJECT}-postgres-1}"
PG_USER="${POSTGRES_USER:-queenswarm}"
PG_DB="${POSTGRES_DB:-queenswarm}"
PRIMARY_ONLY="${1:-}"

if ! docker ps --format '{{.Names}}' | grep -qx "$PG_CONTAINER"; then
  echo "Postgres container not running: ${PG_CONTAINER}" >&2
  echo "Hint: docker compose -p ${COMPOSE_PROJECT} ps" >&2
  exit 1
fi

if [[ "$PRIMARY_ONLY" != "--primary" ]]; then
  echo "== Operator tenant UUID resolver =="
  echo "container: ${PG_CONTAINER}"
  echo
fi

SQL="SELECT id::text, name, created_at::date FROM tenants ORDER BY created_at ASC LIMIT 10;"
rows="$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -tA -F '|' -c "$SQL")"

if [[ -z "${rows// }" ]]; then
  echo "No tenants found — run dashboard seed / bootstrap first." >&2
  exit 1
fi

primary_id=""
primary_name=""
while IFS='|' read -r tid tname tdate; do
  [[ -z "${tid// }" ]] && continue
  if [[ "$PRIMARY_ONLY" != "--primary" ]]; then
    echo "  ${tid}  ${tname}  (${tdate})"
  fi
  if [[ -z "$primary_id" ]]; then
    primary_id="$tid"
    primary_name="$tname"
  fi
done <<<"$rows"

if [[ "$PRIMARY_ONLY" == "--primary" ]]; then
  printf '%s\n' "$primary_id"
  exit 0
fi

echo
if [[ -n "$primary_id" ]]; then
  echo "Suggested QUEEN_MAINTAINER_POST_MERGE_TENANT_ID (oldest tenant):"
  echo "  ${primary_id}  # ${primary_name}"
  echo
  echo "Add to .env.prod:"
  echo "  QUEEN_MAINTAINER_POST_MERGE_TENANT_ID=${primary_id}"
fi
