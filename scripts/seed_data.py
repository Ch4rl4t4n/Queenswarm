#!/usr/bin/env python3
"""Run hive seed inside the Compose backend container (Phase G checklist)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """Exec `docker compose exec backend python scripts/seed_data.py` when possible."""

    os.chdir(ROOT)
    svc = os.environ.get("COMPOSE_BACKEND_SERVICE", "backend")
    cmd = ["docker", "compose", "exec", "-T", svc, "python", "scripts/seed_data.py"]
    proc = subprocess.run(cmd, cwd=ROOT, check=False)  # noqa: S603
    if proc.returncode != 0:
        print("docker compose exec failed — run hive seed manually inside backend:", flush=True)
        print("  python -m scripts.hive_seed", flush=True)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
