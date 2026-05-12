#!/usr/bin/env python3
"""Merge one KEY=value line from local .env into remote /root/Queenswarm/.env."""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from pathlib import Path

REMOTE_MERGE_SCRIPT = Path(__file__).resolve().parent / "remote_merge_env_line.py"
REMOTE_PATH = "/tmp/remote_merge_env_line.py"


def read_value(local_env: Path, key: str) -> str:
    text = local_env.read_text()
    pat = re.compile(rf"^{re.escape(key)}=(.*)$", re.MULTILINE)
    m = pat.search(text)
    if not m:
        msg = f"missing {key} in {local_env}"
        raise SystemExit(msg)
    return m.group(1).strip().strip('"').strip("'")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--key", required=True)
    p.add_argument(
        "--local-env",
        type=Path,
        default=Path(__file__).resolve().parents[1] / ".env",
    )
    p.add_argument(
        "--ssh",
        default=(
            "ssh -i /root/.ssh/queenswarm_prod_ed25519 "
            "-o StrictHostKeyChecking=yes root@46.224.120.151"
        ),
    )
    args = p.parse_args()
    if not REMOTE_MERGE_SCRIPT.is_file():
        msg = f"missing {REMOTE_MERGE_SCRIPT}"
        raise SystemExit(msg)

    value = read_value(args.local_env, args.key)
    ssh_argv = shlex.split(args.ssh)
    if not ssh_argv or ssh_argv[0] != "ssh":
        msg = "--ssh must be an ssh invocation starting with 'ssh'"
        raise SystemExit(msg)

    remote_target = ssh_argv[-1]
    scp_argv = (
        ["scp"]
        + ssh_argv[1:-1]
        + [str(REMOTE_MERGE_SCRIPT), f"{remote_target}:{REMOTE_PATH}"]
    )
    up = subprocess.run(scp_argv, capture_output=True, check=False)
    sys.stdout.buffer.write(up.stdout)
    sys.stderr.buffer.write(up.stderr)
    if up.returncode != 0:
        return int(up.returncode)

    run = subprocess.run(
        [*ssh_argv, "python3", REMOTE_PATH, args.key],
        input=value.encode(),
        capture_output=True,
        check=False,
    )
    sys.stdout.buffer.write(run.stdout)
    sys.stderr.buffer.write(run.stderr)
    return int(run.returncode)


if __name__ == "__main__":
    sys.exit(main())
