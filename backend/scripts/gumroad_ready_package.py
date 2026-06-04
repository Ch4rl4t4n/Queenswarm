#!/usr/bin/env python3
"""Assemble Gumroad ready-to-upload folders from the unified shortlist."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gumroad_cover_asset import (  # noqa: E402
    _listing_hook,
    _listing_title,
    render_cover_brief,
    render_cover_html,
)
from scripts.gumroad_launch_copy_pack import extract_listing_from_bundle, render_launch_copy  # noqa: E402
from scripts.gumroad_upload_tracker import (  # noqa: E402
    UploadProduct,
    load_state,
    parse_shortlist,
    qa_product,
)

EXPORT_ROOT = ROOT.parent / "exports"
DEFAULT_SHORTLIST = EXPORT_ROOT / "UNIFIED_UPLOAD_SHORTLIST.md"
DEFAULT_STATE = EXPORT_ROOT / "gumroad-upload-status.json"
DEFAULT_OUT_DIR = EXPORT_ROOT / "gumroad-ready"


def _uploaded(state: dict[str, Any], slug: str) -> bool:
    """Return True when tracker state marks a product uploaded."""

    products = state.get("products")
    if not isinstance(products, dict):
        return False
    record = products.get(slug)
    return isinstance(record, dict) and record.get("status") == "uploaded"


def _select_products(
    products: list[UploadProduct],
    *,
    state: dict[str, Any],
    all_products: bool,
) -> list[UploadProduct]:
    """Select pending QA-clean products for ready package assembly."""

    selected: list[UploadProduct] = []
    for product in products:
        if _uploaded(state, product.slug) or qa_product(product):
            continue
        selected.append(product)
        if not all_products:
            break
    return selected


def _manifest(product: UploadProduct) -> dict[str, Any]:
    """Return a machine-readable upload package manifest."""

    return {
        "slug": product.slug,
        "kind": product.kind,
        "score": product.score,
        "subtitle": product.subtitle,
        "price": product.price,
        "description": product.description,
        "bundle_file": "product-bundle.tar.gz",
        "gumroad_fields": "GUMROAD_FIELDS.md",
        "cover_html": "cover.html",
        "cover_brief": "COVER_BRIEF.md",
    }


def _readme(product: UploadProduct) -> str:
    """Render operator guidance for one ready package."""

    return "\n".join(
        [
            "# Gumroad Ready Package",
            "",
            f"Product: `{product.slug}`",
            f"Kind: `{product.kind}`",
            f"Price: {product.price}",
            "",
            "## Upload Steps",
            "",
            "1. Create a new Gumroad product.",
            "2. Copy fields from `GUMROAD_FIELDS.md`.",
            "3. Upload `product-bundle.tar.gz` as the product file.",
            "4. Open `cover.html` and capture a 16:9 primary cover image.",
            "5. Use `COVER_BRIEF.md` for preview/proof gallery screenshots.",
            "",
            "After publishing, mark the product uploaded with `gumroad_launch_copy_pack.py --mark-uploaded <slug> --url <gumroad-url>`.",
        ],
    ).rstrip() + "\n"


def write_ready_package(out_root: Path, product: UploadProduct, listing_md: str) -> Path:
    """Write one ready-to-upload product directory."""

    target = out_root / product.slug
    target.mkdir(parents=True, exist_ok=True)
    title = _listing_title(listing_md, product.slug)
    hook = _listing_hook(listing_md, product.subtitle)
    shutil.copy2(Path(product.bundle), target / "product-bundle.tar.gz")
    (target / "GUMROAD_FIELDS.md").write_text(render_launch_copy(product, listing_md), encoding="utf-8")
    (target / "cover.html").write_text(render_cover_html(product, title=title, hook=hook), encoding="utf-8")
    (target / "COVER_BRIEF.md").write_text(render_cover_brief(product, title=title), encoding="utf-8")
    (target / "README.md").write_text(_readme(product), encoding="utf-8")
    (target / "manifest.json").write_text(json.dumps(_manifest(product), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def build_ready_packages(
    out_root: Path,
    products: list[UploadProduct],
    *,
    state: dict[str, Any],
    all_products: bool = False,
) -> list[Path]:
    """Build ready-to-upload directories for next or all QA-clean pending products."""

    written: list[Path] = []
    for product in _select_products(products, state=state, all_products=all_products):
        listing_md = extract_listing_from_bundle(Path(product.bundle), product.listing_path)
        if not listing_md:
            continue
        written.append(write_ready_package(out_root, product, listing_md))
    return written


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shortlist", default=str(DEFAULT_SHORTLIST))
    parser.add_argument("--state", default=str(DEFAULT_STATE))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--all", action="store_true", help="Build packages for every pending QA-clean product.")
    args = parser.parse_args(argv)

    shortlist_path = Path(args.shortlist).expanduser().resolve()
    if not shortlist_path.is_file():
        print(f"Missing shortlist: {shortlist_path}")
        return 1
    products = parse_shortlist(shortlist_path.read_text(encoding="utf-8"))
    state = load_state(Path(args.state).expanduser().resolve())
    written = build_ready_packages(
        Path(args.out_dir).expanduser().resolve(),
        products,
        state=state,
        all_products=bool(args.all),
    )
    if not written:
        print("No pending QA-clean upload product found.")
        return 1
    for target in written:
        print(f"ready_dir={target}")
        print(f"fields={target / 'GUMROAD_FIELDS.md'}")
        print(f"bundle={target / 'product-bundle.tar.gz'}")
        print(f"cover={target / 'cover.html'}")
    print(f"count={len(written)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
