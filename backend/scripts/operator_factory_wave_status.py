#!/usr/bin/env python3
"""MK6 operator CLI — factory catalog wave status + pending seeds."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.application.services.factory_catalog_wave import build_factory_catalog_wave, pending_vertical_seeds


def main(argv: list[str] | None = None) -> int:
    """Print wave progress and optional pending seed list."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", default="", help="Override exports/ root")
    parser.add_argument("--list-pending", action="store_true", help="Print all pending vertical seeds")
    args = parser.parse_args(argv)

    export_root = Path(args.export_root).expanduser().resolve() if args.export_root else None
    wave = build_factory_catalog_wave(export_root)
    print(f"current_wave={wave.current_wave}")
    print(f"scorecard_clean={wave.scorecard_clean_count}/{wave.mk6_target}")
    print(f"catalog_deduped={wave.catalog_deduped_count}")
    print(f"gap_to_next_wave={wave.gap_to_next_wave}")
    print(f"seed_pending={wave.seed_pending_count}/{wave.seed_total}")
    print(f"next_action={wave.next_operator_action}")

    if args.list_pending:
        for seed in pending_vertical_seeds(export_root):
            print(f"  - {seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
