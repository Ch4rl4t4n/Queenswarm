"""Read-only tech health signals for AI harness snapshot (no network)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.core.repo_root import resolve_repo_root

logger = get_logger(__name__)

_PIN_RE = re.compile(r"^[a-zA-Z0-9_.\-]+==[0-9.]+")


def _read_requirements_pins(path: Path) -> list[str]:
    if not path.is_file():
        return []
    pins: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if _PIN_RE.match(text.split(";")[0].strip()):
            pins.append(text.split(";")[0].strip())
    return pins[:40]


def _read_package_json(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    deps: dict[str, str] = {}
    for section in ("dependencies", "devDependencies"):
        block = payload.get(section)
        if isinstance(block, dict):
            for key, val in block.items():
                deps[str(key)] = str(val)
    return deps


def build_tech_health_report(*, repo_root: Path | None = None) -> dict[str, Any]:
    """Scan repository for maintainer-relevant signals (read-only, no network).

    Args:
        repo_root: Override repo root; defaults to detected monorepo root.

    Returns:
        Structured health payload for harness snapshot.
    """
    root = repo_root or resolve_repo_root()
    backend = root / "backend"
    frontend = root / "frontend"

    requirements = _read_requirements_pins(backend / "requirements.txt")
    package_deps = _read_package_json(frontend / "package.json")

    signals: list[str] = []
    if not requirements:
        signals.append("backend_requirements_missing_or_unpinned")
    if len(package_deps) < 5:
        signals.append("frontend_package_json_sparse")
    if not (root / "docs" / "harness" / "QUEEN_MAINTAINER_INSTRUCTIONS.md").is_file():
        signals.append("maintainer_instructions_missing")

    coverage_gate = backend / ".coveragerc"
    perf_tests = frontend / "lib" / "cockpit-performance-budget.test.ts"

    return {
        "repo_root": str(root),
        "backend": {
            "requirements_pinned_count": len(requirements),
            "requirements_sample": requirements[:8],
            "coverage_config_present": coverage_gate.is_file(),
        },
        "frontend": {
            "dependency_count": len(package_deps),
            "sample_dependencies": dict(list(package_deps.items())[:8]),
            "perf_budget_test_present": perf_tests.is_file(),
        },
        "harness": {
            "design_patterns_doc": (root / "docs" / "QUEENSWARM_DESIGN_PATTERNS.md").is_file(),
            "maintainer_instructions": (root / "docs" / "harness" / "QUEEN_MAINTAINER_INSTRUCTIONS.md").is_file(),
        },
        "signals": signals,
        "health_score": max(0.0, min(1.0, 1.0 - len(signals) * 0.15)),
    }


__all__ = ["build_tech_health_report"]
