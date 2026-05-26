#!/usr/bin/env bash
# Security gates: dependency audits + repository secret hygiene checks.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

# Strict mode is default now that dependency baseline is clean.
# Set SECURITY_STRICT=0 only for temporary baseline-diff diagnostics.
SECURITY_STRICT="${SECURITY_STRICT:-1}"
BASELINE_DIR="${ROOT}/security"
PIP_BASELINE="${BASELINE_DIR}/pip-audit-baseline.json"
NPM_BASELINE="${BASELINE_DIR}/npm-audit-baseline.json"

mkdir -p "${BASELINE_DIR}"

echo "[security] backend dependency audit (pip-audit)"
PYTHON_BIN="${ROOT}/backend/venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "No python interpreter found for pip-audit"
  exit 1
fi
"${PYTHON_BIN}" -m pip install --disable-pip-version-check --quiet pip-audit
pip_json="$(mktemp)"
"${PYTHON_BIN}" -m pip_audit -r "${ROOT}/backend/requirements.txt" --progress-spinner off --format json > "${pip_json}" || true

echo "[security] frontend dependency audit (npm audit high)"
cd "${ROOT}/frontend"
npm_json="$(mktemp)"
npm audit --audit-level=high --json > "${npm_json}" || true
cd "${ROOT}"

echo "[security] dependency baseline check (strict=${SECURITY_STRICT})"
python3 <<PY
from __future__ import annotations

import json
from pathlib import Path
import sys

strict = "${SECURITY_STRICT}" == "1"
pip_report = Path("${pip_json}")
npm_report = Path("${npm_json}")
pip_baseline_path = Path("${PIP_BASELINE}")
npm_baseline_path = Path("${NPM_BASELINE}")

def load_json(path: Path) -> object:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    return json.loads(text)

def pip_items(payload: object) -> set[str]:
    data = payload if isinstance(payload, dict) else {}
    vulns = data.get("dependencies", [])
    out: set[str] = set()
    if isinstance(vulns, list):
        for dep in vulns:
            if not isinstance(dep, dict):
                continue
            name = str(dep.get("name", "")).strip()
            for vuln in dep.get("vulns", []) or []:
                if not isinstance(vuln, dict):
                    continue
                vid = str(vuln.get("id", "")).strip()
                if name and vid:
                    out.add(f"{name}|{vid}")
    return out

def npm_items(payload: object) -> set[str]:
    data = payload if isinstance(payload, dict) else {}
    vulns = data.get("vulnerabilities", {})
    out: set[str] = set()
    if not isinstance(vulns, dict):
        return out
    for package, info in vulns.items():
        if not isinstance(info, dict):
            continue
        via = info.get("via", [])
        if isinstance(via, list):
            for entry in via:
                if isinstance(entry, dict):
                    sid = entry.get("source")
                    if sid:
                        out.add(f"{package}|{sid}")
        if not via:
            sev = str(info.get("severity", "unknown"))
            out.add(f"{package}|severity:{sev}")
    return out

current_pip = pip_items(load_json(pip_report))
current_npm = npm_items(load_json(npm_report))

if strict:
    if current_pip or current_npm:
        print("Strict security mode failed.")
        print(f" - pip findings: {len(current_pip)}")
        print(f" - npm findings: {len(current_npm)}")
        sys.exit(1)
    print("Strict security mode passed (no dependency findings).")
    sys.exit(0)

if not pip_baseline_path.exists():
    pip_baseline_path.write_text(json.dumps(sorted(current_pip), indent=2) + "\n", encoding="utf-8")
if not npm_baseline_path.exists():
    npm_baseline_path.write_text(json.dumps(sorted(current_npm), indent=2) + "\n", encoding="utf-8")

baseline_pip = set(load_json(pip_baseline_path))
baseline_npm = set(load_json(npm_baseline_path))
new_pip = sorted(current_pip - baseline_pip)
new_npm = sorted(current_npm - baseline_npm)

print(f"Dependency findings (current): pip={len(current_pip)} npm={len(current_npm)}")
print(f"Dependency findings (baseline): pip={len(baseline_pip)} npm={len(baseline_npm)}")
if new_pip or new_npm:
    print("New dependency vulnerabilities detected beyond baseline:")
    for item in new_pip:
        print(f" - pip: {item}")
    for item in new_npm:
        print(f" - npm: {item}")
    sys.exit(1)

print("Dependency baseline check passed (no new vulnerabilities).")
PY

rm -f "${pip_json}" "${npm_json}"

echo "[security] git-tracked env file policy"
python3 <<'PY'
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

allowed = {
    ".env.example",
    ".env.prod.example",
    ".env.production.example",
    ".env.prod.oauth.example",
    ".env.prod.tokens.example",
    ".env.solo.example",
    "backend/.env.example",
    "frontend/.env.development",
}

tracked = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
violations: list[str] = []
for path in tracked:
    if not Path(path).exists():
        continue
    if not path.startswith(".env") and "/.env" not in path:
        continue
    if path in allowed:
        continue
    violations.append(path)

if violations:
    print("Tracked env policy violations:")
    for item in violations:
        print(f" - {item}")
    sys.exit(1)
PY

echo "[security] static secret pattern scan"
python3 <<'PY'
from __future__ import annotations

from pathlib import Path
import re
import sys

root = Path(".").resolve()

exclude_parts = {
    ".git",
    "node_modules",
    ".next",
    "dist",
    "build",
    "venv",
    ".venv",
    ".venv-ci",
    "assets",
    "backups",
    "tests",
}
exclude_suffixes = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip", ".gz", ".tar", ".ico", ".lock"}
allow_files = {
    ".env.example",
    ".env.prod.example",
    ".env.production.example",
    ".env.prod.oauth.example",
    ".env.prod.tokens.example",
    ".env.solo.example",
    "backend/.env.example",
}

patterns = [
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_pat", re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH|DSA) PRIVATE KEY-----")),
]

hits: list[tuple[str, str]] = []
for path in root.rglob("*"):
    rel = path.relative_to(root).as_posix()
    if any(part in exclude_parts or part.startswith(".venv") for part in path.parts):
        continue
    if not path.is_file():
        continue
    if rel in allow_files:
        continue
    if path.suffix.lower() in exclude_suffixes:
        continue
    try:
        size = path.stat().st_size
    except OSError:
        continue
    if size > 1_000_000:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for name, pattern in patterns:
        if pattern.search(text):
            hits.append((rel, name))
            break

if hits:
    print("Secret pattern scan found suspicious content:")
    for rel, name in hits:
        print(f" - {rel} ({name})")
    sys.exit(1)
PY

echo "[security] gates passed"
