"""Phase 5.2 — deployment helper scripts exist (repo integrity)."""

from __future__ import annotations

from pathlib import Path


def test_phase52_edge_scripts_exist() -> None:
    """Smoke and health scripts must ship for operator validation."""

    root = Path(__file__).resolve().parents[2]
    for rel in (
        "scripts/smoke-edge.sh",
        "scripts/health-check.sh",
        "scripts/deploy-prod.sh",
        "docs/PHASE52_PRODUCTION_READINESS_CHECKLIST.md",
    ):
        assert (root / rel).is_file(), f"missing {rel}"
