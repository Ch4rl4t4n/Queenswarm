#!/usr/bin/env python3
"""Generate copy-paste launch copy for the next Gumroad upload."""

from __future__ import annotations

import argparse
import re
import sys
import tarfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gumroad_upload_tracker import (
    UploadProduct,
    apply_uploaded_mark,
    cover_checklist,
    load_state,
    parse_shortlist,
    qa_product,
    save_state,
)

EXPORT_ROOT = ROOT.parent / "exports"
DEFAULT_SHORTLIST = EXPORT_ROOT / "UNIFIED_UPLOAD_SHORTLIST.md"
DEFAULT_STATE = EXPORT_ROOT / "gumroad-upload-status.json"
DEFAULT_OUTPUT = EXPORT_ROOT / "GUMROAD_LAUNCH_COPY.md"


def _product_record(state: dict[str, Any], slug: str) -> dict[str, Any]:
    """Return tracker record for a product."""

    products = state.get("products")
    if not isinstance(products, dict):
        return {}
    record = products.get(slug)
    return record if isinstance(record, dict) else {}


def select_launch_product(products: list[UploadProduct], state: dict[str, Any]) -> UploadProduct | None:
    """Select the first pending product without upload QA issues."""

    for product in products:
        if _product_record(state, product.slug).get("status") == "uploaded":
            continue
        if qa_product(product):
            continue
        return product
    return None


def prepare_next_launch_product(
    products: list[UploadProduct],
    state: dict[str, Any],
    *,
    mark_uploaded_slug: str = "",
    gumroad_url: str = "",
) -> tuple[UploadProduct | None, dict[str, Any]]:
    """Optionally mark one product uploaded, then select the next launch candidate."""

    if mark_uploaded_slug:
        known_slugs = {product.slug for product in products}
        if mark_uploaded_slug not in known_slugs:
            raise ValueError(f"unknown_slug:{mark_uploaded_slug}")
        state = apply_uploaded_mark(state, slug=mark_uploaded_slug, gumroad_url=gumroad_url)
    return select_launch_product(products, state), state


def extract_listing_from_bundle(bundle_path: Path, listing_path: str) -> str:
    """Read a listing markdown file from a Gumroad tarball."""

    try:
        with tarfile.open(bundle_path, "r:gz") as tar:
            member = tar.getmember(listing_path)
            extracted = tar.extractfile(member)
            if extracted is None:
                return ""
            return extracted.read().decode("utf-8")
    except (KeyError, OSError, tarfile.TarError, UnicodeDecodeError):
        return ""


def _listing_title(listing_md: str, fallback: str) -> str:
    """Extract listing title from markdown when present."""

    for pattern in (r"^\*\*Title:\*\*\s*(.+)$", r"^#\s+(.+)$"):
        match = re.search(pattern, listing_md, re.MULTILINE | re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            if title and title.lower() not in {"listing.md", "listing"}:
                return title
    return fallback


def _listing_hook(listing_md: str, fallback: str) -> str:
    """Extract the strongest short hook for launch copy."""

    match = re.search(r"^\*\*Hook:\*\*\s*(.+?)(?=\n\s*\n|\Z)", listing_md, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if match:
        return " ".join(match.group(1).split())
    return fallback


def _tags_for_product(product: UploadProduct) -> str:
    """Return Gumroad-friendly tags."""

    if product.kind == "content_pack":
        return "content-pack, marketing, social-media, queenswarm, simulate-first"
    if product.kind.startswith("skill_factory"):
        return "agent-skill, automation, queenswarm, simulate-first, workflow"
    return "queenswarm, digital-product, simulate-first"


def render_launch_copy(product: UploadProduct, listing_md: str) -> str:
    """Render one copy-paste launch document for Gumroad and social launch."""

    title = _listing_title(listing_md, product.slug)
    hook = _listing_hook(listing_md, product.subtitle)
    cover_items = "; ".join(cover_checklist(product))
    lines = [
        "# Gumroad Launch Copy",
        "",
        f"Product: `{product.slug}`",
        f"Bundle: `{product.bundle}`",
        f"Listing: `{product.listing_path}`",
        "",
        "## Gumroad Fields",
        "",
        f"**Title:** {title}",
        f"**Subtitle:** {product.subtitle}",
        f"**Price:** {product.price}",
        f"**Tags:** {_tags_for_product(product)}",
        f"**Cover:** {cover_items}",
        "",
        "## Description",
        "",
        product.description or hook,
        "",
        "## Launch Post",
        "",
        f"New Queenswarm drop: {title}",
        "",
        hook,
        "",
        f"Includes a simulate-first bundle you can upload/use today: {Path(product.bundle).name}",
        "",
        "Reply if you want the workflow adapted to your niche.",
        "",
        "## Source LISTING.md",
        "",
        "```markdown",
        listing_md.strip(),
        "```",
    ]
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shortlist", default=str(DEFAULT_SHORTLIST))
    parser.add_argument("--state", default=str(DEFAULT_STATE))
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--mark-uploaded", default="", help="Mark slug as uploaded before generating next launch copy.")
    parser.add_argument("--url", default="", help="Gumroad URL for --mark-uploaded.")
    args = parser.parse_args(argv)

    shortlist_path = Path(args.shortlist).expanduser().resolve()
    if not shortlist_path.is_file():
        print(f"Missing shortlist: {shortlist_path}")
        return 1
    products = parse_shortlist(shortlist_path.read_text(encoding="utf-8"))
    state_path = Path(args.state).expanduser().resolve()
    state = load_state(state_path)
    try:
        product, state = prepare_next_launch_product(
            products,
            state,
            mark_uploaded_slug=str(args.mark_uploaded or ""),
            gumroad_url=str(args.url or ""),
        )
    except ValueError as exc:
        print(str(exc))
        return 1
    if args.mark_uploaded:
        save_state(state_path, state)
        print(f"marked_uploaded={args.mark_uploaded}")
    if product is None:
        print("No pending QA-clean upload product found.")
        return 1

    listing_md = extract_listing_from_bundle(Path(product.bundle), product.listing_path)
    if not listing_md:
        print(f"Could not read listing: {product.listing_path} from {product.bundle}")
        return 1

    rendered = render_launch_copy(product, listing_md)
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    print(rendered.rstrip())
    print(f"\nout={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
