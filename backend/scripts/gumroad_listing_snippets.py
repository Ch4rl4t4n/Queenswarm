#!/usr/bin/env python3
"""Print Gumroad copy-paste snippets from exported skill LISTING.md files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_CANDIDATES = (
    ROOT.parent / "exports" / "skill-factory",
    Path("/tmp/skill-factory-exports"),
)


def _resolve_src() -> Path | None:
    for path in _CANDIDATES:
        if path.is_dir():
            return path
    return None


def _section(md: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, md, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def main() -> int:
    src = _resolve_src()
    if src is None:
        print("Missing skill export dir — run factory-first-revenue-bootstrap.sh first.")
        return 1

    print("== Gumroad listing snippets (manual upload) ==")
    print(f"source={src}")
    for listing_path in sorted(src.glob("*/LISTING.md")):
        slug = listing_path.parent.name
        text = listing_path.read_text(encoding="utf-8")
        hook = _section(text, "One-line hook (Gumroad subtitle)") or _section(text, "One-line hook")
        price = _section(text, "Price anchor")
        short = _section(text, "Short description")
        print(f"\n--- {slug} ---")
        print(f"subtitle: {hook.splitlines()[0][:120] if hook else 'n/a'}")
        if price:
            print(f"price: {price.splitlines()[0][:80]}")
        if short:
            print(f"description: {short.splitlines()[0][:200]}")
        print(f"files: exports/gumroad-upload/{slug}.tar.gz")
        print(f"full_listing: {listing_path}")

    print("\nUpload: https://gumroad.com/products/new")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
