#!/usr/bin/env python3
"""Enable or disable solo optional platform modules (environment column overrides)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.application.services.platform_feature_policy import (
    delete_policy_override,
    load_policy_overrides,
    upsert_policy_overrides,
)
from app.application.services.solo_mode import SOLO_OPTIONAL_FEATURES
from app.core.database import async_session
from app.infrastructure.persistence.models import load_all_models


async def apply_solo_modules(*, enable: bool) -> dict[str, bool]:
    """Persist environment-column overrides for all solo optional features."""

    load_all_models()
    async with async_session() as session:
        if enable:
            updates = [
                {"feature_key": key, "profile_key": "environment", "enabled": True}
                for key in sorted(SOLO_OPTIONAL_FEATURES)
            ]
            merged = await upsert_policy_overrides(session, updates=updates)
        else:
            for key in sorted(SOLO_OPTIONAL_FEATURES):
                await delete_policy_override(session, feature_key=key, profile_key="environment")
            merged = await load_policy_overrides(session)
        await session.commit()
        return {key: bool(merged.get((key, "environment"))) for key in sorted(SOLO_OPTIONAL_FEATURES)}


def main() -> None:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description="Toggle solo optional platform modules in admin matrix.")
    parser.add_argument(
        "--disable",
        action="store_true",
        help="Remove environment overrides (revert to solo defaults: optional modules off).",
    )
    args = parser.parse_args()
    state = asyncio.run(apply_solo_modules(enable=not args.disable))
    action = "disabled" if args.disable else "enabled"
    print(f"solo_optional_modules_{action}:")
    for key, enabled in state.items():
        mark = "on" if enabled else "off"
        print(f"  {key}: {mark}")


if __name__ == "__main__":
    main()
