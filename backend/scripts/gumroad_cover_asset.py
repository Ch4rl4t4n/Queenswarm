#!/usr/bin/env python3
"""Generate Gumroad cover and screenshot brief assets for the next launch product."""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gumroad_launch_copy_pack import (  # noqa: E402
    extract_listing_from_bundle,
    select_launch_product,
)
from scripts.gumroad_upload_tracker import (  # noqa: E402
    UploadProduct,
    cover_checklist,
    load_state,
    parse_shortlist,
    qa_product,
)

EXPORT_ROOT = ROOT.parent / "exports"
DEFAULT_SHORTLIST = EXPORT_ROOT / "UNIFIED_UPLOAD_SHORTLIST.md"
DEFAULT_STATE = EXPORT_ROOT / "gumroad-upload-status.json"
DEFAULT_OUT_DIR = EXPORT_ROOT / "gumroad-assets"


def _listing_title(listing_md: str, fallback: str) -> str:
    """Extract title from listing markdown."""

    match = re.search(r"^\*\*Title:\*\*\s*(.+)$", listing_md, re.MULTILINE | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return fallback


def _listing_hook(listing_md: str, fallback: str) -> str:
    """Extract hook from listing markdown."""

    match = re.search(r"^\*\*Hook:\*\*\s*(.+?)(?=\n\s*\n|\Z)", listing_md, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if match:
        return " ".join(match.group(1).split())
    return fallback


def render_cover_html(product: UploadProduct, *, title: str, hook: str) -> str:
    """Render standalone neon-dark Gumroad cover HTML."""

    safe_title = html.escape(title)
    safe_hook = html.escape(hook)
    safe_kind = html.escape(product.kind.replace("_", " ").title())
    safe_price = html.escape(product.price or "Launch pack")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_title} - Queenswarm Gumroad Cover</title>
  <style>
    :root {{
      --bg: #050510;
      --pollen: #FFB800;
      --cyan: #00FFFF;
      --green: #00FF88;
      --magenta: #FF00AA;
      --text: #F8FAFC;
      --muted: #B8C0D9;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background:
        radial-gradient(circle at 20% 10%, rgba(255, 184, 0, 0.25), transparent 28%),
        radial-gradient(circle at 80% 20%, rgba(0, 255, 255, 0.18), transparent 30%),
        linear-gradient(135deg, #050510 0%, #0B1028 100%);
      color: var(--text);
      font-family: "Space Grotesk", Inter, system-ui, sans-serif;
    }}
    .cover {{
      width: min(1200px, 92vw);
      aspect-ratio: 16 / 9;
      padding: 72px;
      border: 1px solid rgba(255, 184, 0, 0.45);
      background: rgba(5, 5, 16, 0.86);
      box-shadow: 0 0 80px rgba(255, 184, 0, 0.22), inset 0 0 50px rgba(0, 255, 255, 0.08);
      clip-path: polygon(4% 0, 96% 0, 100% 8%, 100% 92%, 96% 100%, 4% 100%, 0 92%, 0 8%);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      overflow: hidden;
      position: relative;
    }}
    .cover::before {{
      content: "";
      position: absolute;
      inset: 32px;
      background-image:
        linear-gradient(30deg, rgba(255, 184, 0, 0.16) 12%, transparent 12.5%, transparent 87%, rgba(255, 184, 0, 0.16) 87.5%),
        linear-gradient(150deg, rgba(255, 184, 0, 0.16) 12%, transparent 12.5%, transparent 87%, rgba(255, 184, 0, 0.16) 87.5%);
      background-size: 84px 48px;
      opacity: 0.2;
      pointer-events: none;
    }}
    .badge {{
      align-self: flex-start;
      color: var(--bg);
      background: var(--pollen);
      border-radius: 999px;
      padding: 10px 18px;
      font: 700 18px/1 "JetBrains Mono", monospace;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    h1 {{
      max-width: 920px;
      margin: 0;
      font-size: clamp(48px, 6vw, 92px);
      line-height: 0.96;
      letter-spacing: -0.055em;
      text-shadow: 0 0 30px rgba(255, 184, 0, 0.22);
    }}
    .hook {{
      max-width: 900px;
      margin: 24px 0 0;
      color: var(--muted);
      font-size: clamp(24px, 2.5vw, 36px);
      line-height: 1.18;
    }}
    .footer {{
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 28px;
      font-family: "JetBrains Mono", monospace;
      color: var(--cyan);
      font-size: 20px;
      position: relative;
      z-index: 1;
    }}
    .proof {{ color: var(--green); }}
    .price {{ color: var(--pollen); }}
  </style>
</head>
<body>
  <main class="cover">
    <div class="badge">Queenswarm / {safe_kind}</div>
    <section>
      <h1>{safe_title}</h1>
      <p class="hook">{safe_hook}</p>
    </section>
    <footer class="footer">
      <span class="proof">simulate-first verified bundle</span>
      <span class="price">{safe_price}</span>
    </footer>
  </main>
</body>
</html>
"""


def render_cover_brief(product: UploadProduct, *, title: str) -> str:
    """Render operator instructions for Gumroad visual assets."""

    lines = [
        "# Gumroad Cover Brief",
        "",
        f"Product: `{product.slug}`",
        f"Title: {title}",
        f"Bundle: `{product.bundle}`",
        "",
        "## Required Assets",
        "",
    ]
    for item in cover_checklist(product):
        lines.append(f"- [ ] {item}")
    lines.extend(
        [
            "",
            "## Screenshot Guidance",
            "",
            "- Open `cover.html` in a browser and capture a 16:9 screenshot.",
            "- Add one internal preview screenshot from the bundle contents.",
            "- Add one proof screenshot showing simulate-first / verified workflow language.",
            "",
            "## Gumroad Placement",
            "",
            "- Use the `cover.html` screenshot as the primary cover.",
            "- Add preview/proof screenshots as gallery images.",
        ],
    )
    return "\n".join(lines).rstrip() + "\n"


def write_cover_assets(out_root: Path, product: UploadProduct, *, title: str, hook: str) -> Path:
    """Write cover HTML and brief files for one product."""

    target = out_root / product.slug
    target.mkdir(parents=True, exist_ok=True)
    (target / "cover.html").write_text(render_cover_html(product, title=title, hook=hook), encoding="utf-8")
    (target / "COVER_BRIEF.md").write_text(render_cover_brief(product, title=title), encoding="utf-8")
    return target


def _uploaded(state: dict, slug: str) -> bool:
    """Return True if tracker state marks a product uploaded."""

    products = state.get("products")
    if not isinstance(products, dict):
        return False
    record = products.get(slug)
    return isinstance(record, dict) and record.get("status") == "uploaded"


def generate_cover_assets(
    out_root: Path,
    products: list[UploadProduct],
    *,
    state: dict,
    all_products: bool = False,
) -> list[Path]:
    """Generate cover assets for the next or all QA-clean pending products."""

    selected: list[UploadProduct]
    if all_products:
        selected = [
            product
            for product in products
            if not _uploaded(state, product.slug) and not qa_product(product)
        ]
    else:
        product = select_launch_product(products, state)
        selected = [product] if product else []

    written: list[Path] = []
    for product in selected:
        listing_md = extract_listing_from_bundle(Path(product.bundle), product.listing_path)
        title = _listing_title(listing_md, product.slug)
        hook = _listing_hook(listing_md, product.subtitle)
        written.append(write_cover_assets(out_root, product, title=title, hook=hook))
    return written


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shortlist", default=str(DEFAULT_SHORTLIST))
    parser.add_argument("--state", default=str(DEFAULT_STATE))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--all", action="store_true", help="Generate assets for every pending QA-clean product.")
    args = parser.parse_args(argv)

    shortlist_path = Path(args.shortlist).expanduser().resolve()
    if not shortlist_path.is_file():
        print(f"Missing shortlist: {shortlist_path}")
        return 1
    products = parse_shortlist(shortlist_path.read_text(encoding="utf-8"))
    state = load_state(Path(args.state).expanduser().resolve())
    written = generate_cover_assets(
        Path(args.out_dir).expanduser().resolve(),
        products,
        state=state,
        all_products=bool(args.all),
    )
    if not written:
        print("No pending QA-clean upload product found.")
        return 1

    for target in written:
        print(f"cover_dir={target}")
        print(f"cover_html={target / 'cover.html'}")
        print(f"cover_brief={target / 'COVER_BRIEF.md'}")
    print(f"count={len(written)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
