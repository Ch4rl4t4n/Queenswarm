#!/usr/bin/env bash
# Zip Skill Factory export bundles for manual Gumroad upload.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/exports/skill-factory"
OUT="$ROOT/exports/gumroad-upload"

if [[ ! -d "$SRC" ]]; then
  echo "Missing $SRC — run factory-first-revenue-bootstrap.sh first."
  exit 1
fi

mkdir -p "$OUT"
count=0
for dir in "$SRC"/*/; do
  [[ -d "$dir" ]] || continue
  slug="$(basename "$dir")"
  if [[ ! -f "$dir/LISTING.md" ]]; then
    echo "skip $slug (no LISTING.md)"
    continue
  fi
  archive="$OUT/${slug}.zip"
  if command -v zip >/dev/null 2>&1; then
    (cd "$dir" && zip -qr "$archive" .)
  else
    archive="$OUT/${slug}.tar.gz"
    tar -czf "$archive" -C "$dir" .
  fi
  echo "packed $archive"
  count=$((count + 1))
done

echo ""
echo "== Gumroad manual upload =="
echo "Upload each archive from: $OUT"
echo "Copy listing text from exports/skill-factory/<slug>/LISTING.md"
echo "Suggested price: see LISTING.md Price anchor section"
echo "packed=$count"
