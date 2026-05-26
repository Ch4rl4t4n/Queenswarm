"""Read-only tech health signals for Queen Maintainer planning."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

_PIN_RE = re.compile(r"^[a-zA-Z0-9_.\-]+==[0-9.]+")


def _detect_backend_root() -> Path:
    """Walk up from this module to find the backend root (folder with requirements.txt)."""

    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "requirements.txt").is_file() and (candidate / "app").is_dir():
            return candidate
    return here.parents[5]


def resolve_repo_root() -> Path:
    """Return monorepo root.

    Local dev: ``/root/Queenswarm`` (sibling of ``backend/`` and ``frontend/``).
    Docker:    ``/app`` (no monorepo parent — frontend ships as a separate image).
    """

    backend = _detect_backend_root()
    parent = backend.parent
    if (parent / "backend").is_dir() and (parent / "frontend").is_dir():
        return parent
    return backend


def _resolve_backend_root(root: Path) -> Path:
    backend = root / "backend"
    if backend.is_dir():
        return backend
    if (root / "requirements.txt").is_file():
        return root
    return _detect_backend_root()


def _resolve_frontend_root(root: Path) -> Path:
    frontend = root / "frontend"
    if frontend.is_dir():
        return frontend
    sibling = root.parent / "frontend"
    return sibling if sibling.is_dir() else frontend


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
        Structured health payload for supervisor goal injection.
    """
    root = repo_root or resolve_repo_root()
    backend = _resolve_backend_root(root)
    frontend = _resolve_frontend_root(root)

    requirements = _read_requirements_pins(backend / "requirements.txt")
    package_deps = _read_package_json(frontend / "package.json")

    frontend_available = frontend.is_dir()
    signals: list[str] = []
    if not requirements:
        signals.append("backend_requirements_missing_or_unpinned")
    if frontend_available and len(package_deps) < 5:
        signals.append("frontend_package_json_sparse")
    if not (root / "docs" / "harness" / "QUEEN_MAINTAINER_INSTRUCTIONS.md").is_file() and not (
        backend / "docs" / "harness" / "QUEEN_MAINTAINER_INSTRUCTIONS.md"
    ).is_file():
        signals.append("maintainer_instructions_missing")

    coverage_gate = backend / ".coveragerc"
    if not coverage_gate.is_file() and (backend.parent / ".coveragerc").is_file():
        coverage_gate = backend.parent / ".coveragerc"
    perf_tests = frontend / "lib" / "cockpit-performance-budget.test.ts"

    docs_root_candidates = [root / "docs", backend / "docs"]
    design_doc = next(
        (c / "QUEENSWARM_DESIGN_PATTERNS.md" for c in docs_root_candidates if (c / "QUEENSWARM_DESIGN_PATTERNS.md").is_file()),
        root / "docs" / "QUEENSWARM_DESIGN_PATTERNS.md",
    )
    maintainer_doc = next(
        (
            c / "harness" / "QUEEN_MAINTAINER_INSTRUCTIONS.md"
            for c in docs_root_candidates
            if (c / "harness" / "QUEEN_MAINTAINER_INSTRUCTIONS.md").is_file()
        ),
        root / "docs" / "harness" / "QUEEN_MAINTAINER_INSTRUCTIONS.md",
    )

    return {
        "repo_root": str(root),
        "backend": {
            "root": str(backend),
            "requirements_pinned_count": len(requirements),
            "requirements_sample": requirements[:8],
            "coverage_config_present": coverage_gate.is_file(),
        },
        "frontend": {
            "root": str(frontend) if frontend_available else None,
            "available": frontend_available,
            "dependency_count": len(package_deps),
            "sample_dependencies": dict(list(package_deps.items())[:8]),
            "perf_budget_test_present": perf_tests.is_file() if frontend_available else None,
        },
        "harness": {
            "design_patterns_doc": design_doc.is_file(),
            "maintainer_instructions": maintainer_doc.is_file(),
        },
        "signals": signals,
        "health_score": max(0.0, min(1.0, 1.0 - len(signals) * 0.15)),
    }


__all__ = ["build_tech_health_report", "resolve_repo_root"]
