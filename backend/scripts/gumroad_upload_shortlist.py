#!/usr/bin/env python3
"""Rank Gumroad upload candidates from exported Queenswarm bundles."""

from __future__ import annotations

import argparse
import re
import sys
import tarfile
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.content_pack_gumroad_listing_snippets import extract_listing_fields

DEFAULT_EXPORT_DIR = ROOT.parent / "exports" / "gumroad-upload"


def _section(md: str, heading: str) -> str:
    """Extract a markdown section by heading text."""

    pattern = rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, md, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _first_line(text: str) -> str:
    """Return first non-empty line."""

    for line in text.splitlines():
        clean = line.strip().lstrip("-* ").replace("**", "").strip()
        if clean:
            return clean
    return ""


def _read_listing(bundle_path: Path) -> tuple[str, str, str] | None:
    """Return listing markdown, member path, and bundle kind."""

    slug = bundle_path.name.removesuffix(".tar.gz")
    content_pack_member = f"{slug}/LISTING.md"
    try:
        with tarfile.open(bundle_path, "r:gz") as tar:
            members = {member.name: member for member in tar.getmembers() if member.isfile()}
            for name, kind in ((content_pack_member, "content_pack"), ("./LISTING.md", "skill_factory")):
                member = members.get(name)
                if member is None:
                    continue
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                return extracted.read().decode("utf-8"), name, kind
    except (tarfile.TarError, UnicodeDecodeError, OSError):
        return None
    return None


def _skill_fields(listing_md: str) -> dict[str, str]:
    """Extract listing fields from Skill Factory LISTING.md."""

    return {
        "subtitle": _first_line(
            _section(listing_md, "One-line hook (Gumroad subtitle)")
            or _section(listing_md, "One-line hook"),
        ),
        "price": _first_line(_section(listing_md, "Price anchor")),
        "description": _first_line(_section(listing_md, "Short description")),
    }


def _is_draft_listing(listing_md: str, fields: dict[str, str]) -> bool:
    """Return True for generic draft exports that need more review."""

    haystack = " ".join([listing_md, fields.get("subtitle", ""), fields.get("description", "")]).lower()
    return "draft from skill factory session" in haystack or "review before publish" in haystack


def _score_row(*, kind: str, fields: dict[str, str], is_draft: bool) -> int:
    """Score a Gumroad upload candidate for manual prioritization."""

    score = 100 if kind == "content_pack" else 70
    if is_draft:
        score = 20
    if fields.get("price"):
        score += 5
    if fields.get("description"):
        score += 5
    if len(fields.get("subtitle", "")) >= 40:
        score += 5
    return score


def iter_upload_candidates(src: Path, *, include_drafts: bool = False) -> Iterator[dict[str, str | int]]:
    """Yield ranked metadata for exported Gumroad bundles."""

    for bundle_path in sorted(src.glob("*.tar.gz")):
        loaded = _read_listing(bundle_path)
        if loaded is None:
            continue
        listing_md, listing_path, kind = loaded
        fields = extract_listing_fields(listing_md) if kind == "content_pack" else _skill_fields(listing_md)
        is_draft = _is_draft_listing(listing_md, fields)
        if is_draft and not include_drafts:
            continue
        row_kind = "skill_factory_draft" if is_draft else kind
        slug = bundle_path.name.removesuffix(".tar.gz")
        yield {
            "slug": slug,
            "kind": row_kind,
            "score": _score_row(kind=kind, fields=fields, is_draft=is_draft),
            "subtitle": fields.get("subtitle", ""),
            "price": fields.get("price", ""),
            "description": fields.get("description", ""),
            "bundle": str(bundle_path),
            "listing_path": listing_path,
        }


def build_shortlist(src: Path, *, limit: int = 12, include_drafts: bool = False) -> list[dict[str, str | int]]:
    """Build a sorted Gumroad upload shortlist."""

    rows = list(iter_upload_candidates(src, include_drafts=include_drafts))
    rows.sort(key=lambda row: (-int(row["score"]), str(row["kind"]), str(row["slug"])))
    return rows[: max(1, limit)]


def render_markdown(rows: list[dict[str, str | int]]) -> str:
    """Render a Gumroad upload shortlist as an operator checklist."""

    lines = [
        "# Gumroad Upload Shortlist",
        "",
        "Use this checklist for manual Gumroad product creation.",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"- [ ] `{row['slug']}` ({row['kind']}, score {row['score']})",
                f"  - **Subtitle:** {str(row['subtitle']) or 'n/a'}",
            ],
        )
        if row["price"]:
            lines.append(f"  - **Price:** {row['price']}")
        if row["description"]:
            lines.append(f"  - **Description:** {row['description']}")
        lines.extend(
            [
                f"  - **File:** `{row['bundle']}`",
                f"  - **Listing:** `{row['listing_path']}`",
                "",
            ],
        )
    lines.append("Upload: https://gumroad.com/products/new")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    """Print a ranked Gumroad manual upload shortlist."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src", nargs="?", default=str(DEFAULT_EXPORT_DIR))
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--include-drafts", action="store_true")
    parser.add_argument(
        "--write-markdown",
        nargs="?",
        const="UPLOAD_SHORTLIST.md",
        help="Write the shortlist as markdown in the export directory, or to the provided path.",
    )
    args = parser.parse_args(argv)

    src = Path(args.src).expanduser().resolve()
    if not src.is_dir():
        print(f"Missing export dir: {src}")
        return 1

    rows = build_shortlist(src, limit=args.limit, include_drafts=args.include_drafts)
    if args.write_markdown:
        output_path = Path(args.write_markdown)
        if not output_path.is_absolute():
            output_path = src / output_path
        output_path.write_text(render_markdown(rows), encoding="utf-8")
        print(f"markdown={output_path}")

    print("== Gumroad upload shortlist ==")
    print(f"source={src}")
    for index, row in enumerate(rows, start=1):
        print(f"\n{index}. {row['slug']} [{row['kind']}] score={row['score']}")
        print(f"subtitle: {str(row['subtitle'])[:180] or 'n/a'}")
        if row["price"]:
            print(f"price: {str(row['price'])[:80]}")
        if row["description"]:
            print(f"description: {str(row['description'])[:220]}")
        print(f"file: {row['bundle']}")

    print(f"\ncount={len(rows)}")
    print("Upload: https://gumroad.com/products/new")
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
