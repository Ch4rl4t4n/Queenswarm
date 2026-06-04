#!/usr/bin/env python3
"""Score Gumroad upload candidates for sales readiness."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gumroad_upload_tracker import UploadProduct, load_state, parse_shortlist, qa_product  # noqa: E402

EXPORT_ROOT = ROOT.parent / "exports"
DEFAULT_SHORTLIST = EXPORT_ROOT / "UNIFIED_UPLOAD_SHORTLIST.md"
DEFAULT_STATE = EXPORT_ROOT / "gumroad-upload-status.json"
DEFAULT_ASSET_ROOT = EXPORT_ROOT / "gumroad-assets"
DEFAULT_OUTPUT = EXPORT_ROOT / "GUMROAD_SCORECARD.md"


@dataclass(frozen=True)
class ProductScore:
    """Sales-readiness score for one Gumroad product."""

    slug: str
    kind: str
    total: int
    verdict: str
    fixes: list[str] = field(default_factory=list)


def _asset_ready(product: UploadProduct, asset_root: Path) -> bool:
    """Return True when generated cover assets exist."""

    product_dir = asset_root / product.slug
    return (product_dir / "cover.html").is_file() and (product_dir / "COVER_BRIEF.md").is_file()


def _uploaded(state: dict, slug: str) -> bool:
    """Return True when tracker state marks a product uploaded."""

    products = state.get("products")
    if not isinstance(products, dict):
        return False
    record = products.get(slug)
    return isinstance(record, dict) and record.get("status") == "uploaded"


def score_product(product: UploadProduct, *, asset_root: Path, state: dict | None = None) -> ProductScore:
    """Score one product across listing, bundle, visual, and launch readiness."""

    score = 100
    fixes: list[str] = []
    issues = set(qa_product(product))

    penalties = {
        "missing_price": 20,
        "weak_hook": 15,
        "weak_description": 12,
        "bundle_missing": 25,
        "listing_missing": 10,
    }
    for issue, penalty in penalties.items():
        if issue in issues:
            score -= penalty

    if "missing_price" in issues:
        fixes.append("Add explicit price")
    if "weak_hook" in issues:
        fixes.append("Strengthen one-line hook")
    if "weak_description" in issues:
        fixes.append("Clarify buyer and outcome")
    if "bundle_missing" in issues:
        fixes.append("Regenerate or locate upload bundle")
    if "listing_missing" in issues:
        fixes.append("Restore LISTING.md reference")

    if not _asset_ready(product, asset_root):
        score -= 10
        fixes.append("Generate cover assets")

    if state is not None and _uploaded(state, product.slug):
        score = min(score, 100)
        verdict = "uploaded"
    elif score >= 85 and not fixes:
        verdict = "ready"
    elif score >= 70:
        verdict = "review"
    else:
        verdict = "fix_first"

    return ProductScore(
        slug=product.slug,
        kind=product.kind,
        total=max(0, min(100, score)),
        verdict=verdict,
        fixes=fixes,
    )


def render_scorecard_report(scores: list[ProductScore]) -> str:
    """Render product scorecard markdown."""

    ready_count = len([score for score in scores if score.verdict in {"ready", "uploaded"}])
    lines = [
        "# Gumroad Product Scorecard",
        "",
        f"Ready: **{ready_count}/{len(scores)}**",
        "",
        "## Products",
        "",
    ]
    for score in sorted(scores, key=lambda item: (-item.total, item.verdict, item.slug)):
        lines.append(f"- `{score.slug}` — {score.total}/100 {score.verdict} ({score.kind})")
        for fix in score.fixes:
            lines.append(f"  - Fix: {fix}")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shortlist", default=str(DEFAULT_SHORTLIST))
    parser.add_argument("--state", default=str(DEFAULT_STATE))
    parser.add_argument("--asset-root", default=str(DEFAULT_ASSET_ROOT))
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    shortlist_path = Path(args.shortlist).expanduser().resolve()
    if not shortlist_path.is_file():
        print(f"Missing shortlist: {shortlist_path}")
        return 1
    products = parse_shortlist(shortlist_path.read_text(encoding="utf-8"))
    state = load_state(Path(args.state).expanduser().resolve())
    asset_root = Path(args.asset_root).expanduser().resolve()
    scores = [score_product(product, asset_root=asset_root, state=state) for product in products]
    report = render_scorecard_report(scores)
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(report.rstrip())
    print(f"\nout={out_path}")
    return 0 if scores else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
