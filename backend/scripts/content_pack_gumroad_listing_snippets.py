#!/usr/bin/env python3
"""Print Gumroad copy-paste snippets from Content Pack Factory tarballs."""

from __future__ import annotations

import re
import sys
import tarfile
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
_CANDIDATES = (
    ROOT.parent / "exports" / "gumroad-upload",
    Path("/tmp/content-pack-exports"),
)


def _resolve_src(raw: str | None = None) -> Path | None:
    """Resolve a content pack export directory."""

    if raw:
        path = Path(raw).expanduser().resolve()
        return path if path.is_dir() else None
    for path in _CANDIDATES:
        if path.is_dir():
            return path
    return None


def _section(md: str, heading: str) -> str:
    """Extract a markdown section by heading text."""

    pattern = rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, md, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _label(md: str, label: str) -> str:
    """Extract a single markdown bold-label value."""

    pattern = rf"^\*\*{re.escape(label)}:\*\*\s*(.*?)(?=\n\s*\n|\Z)"
    match = re.search(pattern, md, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _first_nonempty_line(text: str) -> str:
    """Return the first non-empty line stripped of bullets."""

    for line in text.splitlines():
        clean = line.strip().lstrip("-* ").strip()
        if clean:
            return clean
    return ""


def extract_listing_fields(listing_md: str) -> dict[str, str]:
    """Extract Gumroad-friendly fields from LISTING.md content."""

    subtitle = (
        _section(listing_md, "One-line hook (Gumroad subtitle)")
        or _section(listing_md, "One-line hook")
        or _section(listing_md, "Hook")
        or _label(listing_md, "Hook")
    )
    price = _section(listing_md, "Price anchor") or _label(listing_md, "Price anchor") or _label(listing_md, "Price")
    description = (
        _section(listing_md, "Short description")
        or _label(listing_md, "Target buyer")
        or _section(listing_md, "What's included")
        or _label(listing_md, "What's included")
    )

    fallback = ""
    for line in listing_md.splitlines():
        clean = line.strip()
        if clean and not clean.startswith("#"):
            fallback = clean
            break

    return {
        "subtitle": _first_nonempty_line(subtitle) or fallback[:160],
        "price": _first_nonempty_line(price),
        "description": _first_nonempty_line(description),
    }


def _read_listing_from_bundle(bundle_path: Path) -> tuple[str, str] | None:
    """Read LISTING.md content and member path from a tar.gz bundle."""

    slug = bundle_path.name.removesuffix(".tar.gz")
    expected_listing = f"{slug}/LISTING.md"
    try:
        with tarfile.open(bundle_path, "r:gz") as tar:
            for member in tar.getmembers():
                if not member.isfile() or member.name != expected_listing:
                    continue
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                return extracted.read().decode("utf-8"), member.name
    except (tarfile.TarError, UnicodeDecodeError, OSError):
        return None
    return None


def iter_content_pack_bundles(src: Path) -> Iterator[dict[str, str]]:
    """Yield Gumroad listing rows for content pack tarballs."""

    for bundle_path in sorted(src.glob("*.tar.gz")):
        listing = _read_listing_from_bundle(bundle_path)
        if listing is None:
            continue
        listing_md, listing_path = listing
        fields = extract_listing_fields(listing_md)
        slug = bundle_path.name.removesuffix(".tar.gz")
        yield {
            "slug": slug,
            "bundle": str(bundle_path),
            "listing_path": listing_path,
            "subtitle": fields["subtitle"],
            "price": fields["price"],
            "description": fields["description"],
        }


def main(argv: list[str] | None = None) -> int:
    """Print manual Gumroad upload snippets."""

    args = list(argv if argv is not None else sys.argv[1:])
    src = _resolve_src(args[0] if args else None)
    if src is None:
        print("Missing content pack export dir — expected exports/gumroad-upload/*.tar.gz.")
        return 1

    print("== Content Pack Gumroad listing snippets (manual upload) ==")
    print(f"source={src}")
    count = 0
    for row in iter_content_pack_bundles(src):
        count += 1
        print(f"\n--- {row['slug']} ---")
        print(f"subtitle: {row['subtitle'][:160] or 'n/a'}")
        if row["price"]:
            print(f"price: {row['price'][:80]}")
        if row["description"]:
            print(f"description: {row['description'][:220]}")
        print(f"files: {row['bundle']}")
        print(f"full_listing: {row['listing_path']}")

    print(f"\ncount={count}")
    print("Upload: https://gumroad.com/products/new")
    return 0 if count else 1


if __name__ == "__main__":
    raise SystemExit(main())
