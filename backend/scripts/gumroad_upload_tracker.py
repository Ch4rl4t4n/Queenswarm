#!/usr/bin/env python3
"""Track manual Gumroad uploads from the unified upload shortlist."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPORT_ROOT = ROOT.parent / "exports"
DEFAULT_SHORTLIST = EXPORT_ROOT / "UNIFIED_UPLOAD_SHORTLIST.md"
DEFAULT_STATE = EXPORT_ROOT / "gumroad-upload-status.json"
DEFAULT_REPORT = EXPORT_ROOT / "UPLOAD_PROGRESS.md"

_PRODUCT_RE = re.compile(r"^- \[[ xX]\] `(?P<slug>[^`]+)` \((?P<kind>[^,]+), score (?P<score>\d+)\)", re.MULTILINE)
_FIELD_RE = re.compile(r"^  - \*\*(?P<name>Subtitle|Price|Description|File|Listing):\*\* (?P<value>.+)$", re.MULTILINE)


@dataclass(frozen=True)
class UploadProduct:
    """One product from the Gumroad upload shortlist."""

    slug: str
    kind: str
    score: int
    subtitle: str = ""
    price: str = ""
    description: str = ""
    bundle: str = ""
    listing_path: str = ""


def _clean_backticks(value: str) -> str:
    """Strip markdown code ticks from a field value."""

    return value.strip().strip("`")


def parse_shortlist(markdown: str) -> list[UploadProduct]:
    """Parse unified upload shortlist markdown into ranked products."""

    matches = list(_PRODUCT_RE.finditer(markdown))
    products: list[UploadProduct] = []
    for index, match in enumerate(matches):
        block_end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        block = markdown[match.end() : block_end]
        fields = {field.group("name").lower(): _clean_backticks(field.group("value")) for field in _FIELD_RE.finditer(block)}
        products.append(
            UploadProduct(
                slug=match.group("slug"),
                kind=match.group("kind"),
                score=int(match.group("score")),
                subtitle=fields.get("subtitle", ""),
                price=fields.get("price", ""),
                description=fields.get("description", ""),
                bundle=fields.get("file", ""),
                listing_path=fields.get("listing", ""),
            ),
        )
    return products


def load_state(path: Path) -> dict[str, Any]:
    """Load upload tracker state from disk."""

    if not path.is_file():
        return {"products": {}}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"products": {}}
    if not isinstance(loaded, dict):
        return {"products": {}}
    products = loaded.get("products")
    if not isinstance(products, dict):
        loaded["products"] = {}
    return loaded


def save_state(path: Path, state: dict[str, Any]) -> None:
    """Persist upload tracker state."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def apply_uploaded_mark(state: dict[str, Any], *, slug: str, gumroad_url: str) -> dict[str, Any]:
    """Mark one product as manually uploaded."""

    products = state.setdefault("products", {})
    if not isinstance(products, dict):
        products = {}
        state["products"] = products
    current = products.get(slug)
    record = dict(current) if isinstance(current, dict) else {}
    record["status"] = "uploaded"
    if gumroad_url.strip():
        record["gumroad_url"] = gumroad_url.strip()
    record["updated_at"] = datetime.now(tz=UTC).isoformat()
    products[slug] = record
    return state


def _product_record(state: dict[str, Any], slug: str) -> dict[str, Any]:
    products = state.get("products")
    if not isinstance(products, dict):
        return {}
    record = products.get(slug)
    return record if isinstance(record, dict) else {}


def render_progress_report(products: list[UploadProduct], state: dict[str, Any], *, next_limit: int = 5) -> str:
    """Render a manual upload progress report."""

    uploaded = [product for product in products if _product_record(state, product.slug).get("status") == "uploaded"]
    pending = [product for product in products if product not in uploaded]
    lines = [
        "# Gumroad Upload Progress",
        "",
        f"Uploaded: **{len(uploaded)}/{len(products)}**",
        "",
        "## Next Uploads",
        "",
    ]
    for product in pending[: max(1, next_limit)]:
        lines.extend(
            [
                f"- [ ] `{product.slug}` ({product.kind}, score {product.score})",
                f"  - **Price:** {product.price or 'n/a'}",
                f"  - **File:** `{product.bundle}`",
            ],
        )
    if not pending:
        lines.append("- All shortlist products are marked uploaded.")

    lines.extend(["", "## Uploaded", ""])
    if uploaded:
        for product in uploaded:
            record = _product_record(state, product.slug)
            url = str(record.get("gumroad_url") or "url-not-recorded")
            lines.append(f"- [x] `{product.slug}` - {url}")
    else:
        lines.append("- None yet.")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shortlist", default=str(DEFAULT_SHORTLIST), help="Unified upload shortlist markdown path.")
    parser.add_argument("--state", default=str(DEFAULT_STATE), help="JSON status file path.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT), help="Progress report markdown path.")
    parser.add_argument("--mark-uploaded", default="", help="Slug to mark uploaded.")
    parser.add_argument("--url", default="", help="Gumroad URL for --mark-uploaded.")
    parser.add_argument("--next", type=int, default=5, help="How many pending products to show.")
    args = parser.parse_args(argv)

    shortlist_path = Path(args.shortlist).expanduser().resolve()
    if not shortlist_path.is_file():
        print(f"Missing shortlist: {shortlist_path}")
        return 1
    products = parse_shortlist(shortlist_path.read_text(encoding="utf-8"))
    if not products:
        print(f"No products found in shortlist: {shortlist_path}")
        return 1

    state_path = Path(args.state).expanduser().resolve()
    state = load_state(state_path)
    if args.mark_uploaded:
        known_slugs = {product.slug for product in products}
        if args.mark_uploaded not in known_slugs:
            print(f"Unknown slug: {args.mark_uploaded}")
            return 1
        state = apply_uploaded_mark(state, slug=args.mark_uploaded, gumroad_url=args.url)
        save_state(state_path, state)
        print(f"marked_uploaded={args.mark_uploaded}")

    report = render_progress_report(products, state, next_limit=max(1, args.next))
    report_path = Path(args.report).expanduser().resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(report.rstrip())
    print(f"\nreport={report_path}")
    print(f"state={state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
