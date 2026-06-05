#!/usr/bin/env python3
"""Sync gumroad-ready manifests into a marketing catalog JSON file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.application.services.marketing_product_catalog import build_catalog  # noqa: E402

DEFAULT_OUT = ROOT.parent / "exports" / "marketing" / "catalog.json"
FRONTEND_MIRROR = ROOT.parent / "frontend" / "content" / "marketing" / "catalog.json"


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", default="", help="Override exports root directory.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Primary catalog JSON output.")
    parser.add_argument("--mirror", default=str(FRONTEND_MIRROR), help="Optional frontend mirror path.")
    args = parser.parse_args(argv)

    export_root = (
        Path(args.export_root).expanduser().resolve()
        if args.export_root
        else (ROOT.parent / "exports").resolve()
    )
    catalog = build_catalog(export_root)
    payload = catalog.model_dump(mode="json")
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"

    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")

    mirror = Path(args.mirror).expanduser().resolve()
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_text(text, encoding="utf-8")

    print(f"products={catalog.product_count} out={out} mirror={mirror}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
