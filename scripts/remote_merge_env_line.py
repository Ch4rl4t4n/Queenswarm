#!/usr/bin/env python3
"""Merge one KEY=value into /root/Queenswarm/.env. Value read from stdin (no echo)."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        msg = "usage: remote_merge_env_line.py KEY"
        raise SystemExit(msg)
    key = sys.argv[1]
    val = sys.stdin.read().strip()
    if not val:
        msg = "empty stdin"
        raise SystemExit(msg)
    path = Path("/root/Queenswarm/.env")
    raw = path.read_text() if path.exists() else ""
    line = f"{key}={val}\n"
    esc = re.escape(key)
    if re.search(rf"^{esc}=", raw, flags=re.M):
        raw = re.sub(rf"^{esc}=.*$", line.rstrip("\n"), raw, count=1, flags=re.M)
    else:
        raw = (raw.rstrip() + "\n" + line) if raw.strip() else line
    path.write_text(raw)
    print("merged", key)


if __name__ == "__main__":
    main()
