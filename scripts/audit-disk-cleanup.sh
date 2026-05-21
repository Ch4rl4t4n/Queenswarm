#!/usr/bin/env bash
# Audit host disk + safely prune unused Queenswarm artifacts (never touches queenswarm_prod).
#
# Usage:
#   ./scripts/audit-disk-cleanup.sh          # dry-run (default)
#   APPLY=1 ./scripts/audit-disk-cleanup.sh  # execute cleanup
#
# Safe targets:
#   - Dev compose project `queenswarm` (duplicate postgres/redis vs prod)
#   - Stg / old dev Docker image tags (not queenswarm_prod-*)
#   - Unused Chroma/Qdrant/postgres:16-alpine images (vector tier = pgvector)
#   - Dangling Docker volumes + build cache older than RETAIN_BUILD_CACHE_HOURS
#   - Duplicate backend/.venv when backend/venv exists
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APPLY="${APPLY:-0}"
RETAIN_BUILD_CACHE_HOURS="${RETAIN_BUILD_CACHE_HOURS:-168}"

log() { printf '%s\n' "$*"; }
run() {
  if [[ "$APPLY" == "1" ]]; then
    log "+ $*"
    "$@"
  else
    log "[dry-run] $*"
  fi
}

log "=== Queenswarm disk audit ($(date -Iseconds)) ==="
df -h / | tail -1
docker system df 2>/dev/null || true
log ""
log "Compose projects:"
docker compose ls 2>/dev/null || true
log ""

if docker compose -p queenswarm ps -q 2>/dev/null | grep -q .; then
  log "Dev stack 'queenswarm' (duplicate infra vs queenswarm_prod):"
  docker compose -p queenswarm -f "$ROOT/docker-compose.yml" ps 2>/dev/null || true
  run docker compose -p queenswarm -f "$ROOT/docker-compose.yml" down --remove-orphans
else
  log "Dev stack 'queenswarm': not running"
fi

prune_images() {
  local pattern="$1"
  while IFS= read -r id; do
    [[ -n "$id" ]] || continue
    run docker rmi -f "$id"
  done < <(docker images --format '{{.ID}}\t{{.Repository}}:{{.Tag}}' \
    | awk -v p="$pattern" '$2 ~ p {print $1}' | sort -u)
}

log ""
log "Removing stale image tags (never queenswarm_prod-*):"
STALE_PATTERNS=(
  '^queenswarm_stg-'
  '^queenswarm_backend:'
  '^queenswarm_celery-'
  '^queenswarm_frontend:'
  '^queenswarm-backend:'
  '^queenswarm-celery-'
  '^queenswarm-frontend:'
  '^chromadb/chroma:'
  '^qdrant/qdrant:'
  '^postgres:16-alpine$'
)
for pat in "${STALE_PATTERNS[@]}"; do
  log "  pattern: $pat"
  if [[ "$APPLY" == "1" ]]; then
    prune_images "$pat"
  else
    docker images --format '{{.Repository}}:{{.Tag}}\t{{.Size}}' | awk -v p="$pat" '$1 ~ p' || true
  fi
done

log ""
log "Prune dangling volumes:"
run docker volume prune -f

log ""
log "Prune build cache older than ${RETAIN_BUILD_CACHE_HOURS}h:"
run docker builder prune -af --filter "until=${RETAIN_BUILD_CACHE_HOURS}h"

if [[ -d "$ROOT/backend/venv" && -d "$ROOT/backend/.venv" ]]; then
  log ""
  log "Duplicate Python venv: backend/.venv ($(du -sh "$ROOT/backend/.venv" | cut -f1)) — keeping backend/venv for gates"
  run rm -rf "$ROOT/backend/.venv"
fi

log ""
log "Removing unused dev compose volumes (queenswarm_* without _prod_):"
while IFS= read -r vol; do
  [[ -n "$vol" ]] || continue
  run docker volume rm -f "$vol"
done < <(docker volume ls --format '{{.Name}}' | grep -E '^queenswarm_' | grep -v '_prod_' || true)

log ""
log "=== After audit ==="
df -h / | tail -1
docker system df 2>/dev/null || true

if [[ "$APPLY" != "1" ]]; then
  log ""
  log "Dry-run only. Re-run with: APPLY=1 $0"
fi
