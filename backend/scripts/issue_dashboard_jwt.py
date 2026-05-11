#!/usr/bin/env python3
"""Emit a long-lived JWT for Grafana/Next hive proxy callers (prints token only)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.jwt_tokens import create_access_token


def main() -> None:
    token, _expires = create_access_token(
        subject="neon-dashboard-bot",
        expires_minutes=60 * 24 * 365,
        scope="dashboard:proxy",
    )
    print(token)


if __name__ == "__main__":
    main()
