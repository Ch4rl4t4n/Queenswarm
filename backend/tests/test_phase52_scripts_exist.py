"""Phase 5.2 — deployment helper scripts exist (repo integrity)."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    """Resolve monorepo root from test file location (host or Docker /app)."""

    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / "scripts" / "smoke-edge.sh").is_file():
            return ancestor
        if (ancestor / "scripts" / "deploy-prod.sh").is_file() and (ancestor / "backend" / "tests").is_dir():
            return ancestor
    msg = "Could not locate repo root (scripts/smoke-edge.sh missing)"
    raise AssertionError(msg)


def test_phase52_edge_scripts_exist() -> None:
    """Smoke and health scripts must ship for operator validation."""

    root = _repo_root()
    for rel in (
        "scripts/smoke-edge.sh",
        "scripts/health-check.sh",
        "scripts/deploy-prod.sh",
        "docs/PHASE52_PRODUCTION_READINESS_CHECKLIST.md",
    ):
        assert (root / rel).is_file(), f"missing {rel}"
