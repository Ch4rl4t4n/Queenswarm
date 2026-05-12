#!/usr/bin/env python3
"""Phase G colony seed wrapper — delegates to ``hive_seed.py``."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def main() -> None:
    """Spawn ``hive_seed`` in the same interpreter for identical bootstrap."""

    hive_seed_path = _HERE / "hive_seed.py"
    code = subprocess.call([sys.executable, str(hive_seed_path)])  # noqa: S603
    sys.exit(code)


if __name__ == "__main__":
    main()
