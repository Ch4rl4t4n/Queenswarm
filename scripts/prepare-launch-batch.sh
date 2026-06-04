#!/usr/bin/env bash
# Export top sellable skills + LAUNCH_CHECKLIST.md for Gumroad manual upload.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIMIT="${1:-3}"

if docker ps --format '{{.Names}}' | grep -q 'queenswarm_prod-backend-1'; then
  docker exec queenswarm_prod-backend-1 python scripts/factory_prepare_launch_batch.py --limit "$LIMIT"
  mkdir -p "$ROOT/exports/launch-batch"
  docker cp queenswarm_prod-backend-1:/app/exports/launch-batch/. "$ROOT/exports/launch-batch/" 2>/dev/null || true
else
  cd "$ROOT/backend" && .venv-test/bin/python scripts/factory_prepare_launch_batch.py --limit "$LIMIT"
fi

OUT="$ROOT/exports/launch-batch"
if [[ -d "$OUT" ]]; then
  mkdir -p "$ROOT/exports/gumroad-upload"
  for dir in "$OUT"/*/; do
    [[ -d "$dir" ]] || continue
    slug="$(basename "$dir")"
    [[ "$slug" == *.* ]] && continue
    archive="$ROOT/exports/gumroad-upload/${slug}.tar.gz"
    tar -czf "$archive" -C "$dir" .
    echo "packed $archive"
  done
fi

echo ""
echo "== Next: Gumroad manual upload =="
echo "Read: $OUT/LAUNCH_CHECKLIST.md"
echo "Upload: exports/gumroad-upload/*.tar.gz"
