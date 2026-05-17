"""Phase 3 — Communication & Knowledge connector templates + vault sync helpers."""

from __future__ import annotations

from app.infrastructure.connectors.phase3.catalog import (
    PHASE3_TEMPLATE_INDEX,
    Phase3ConnectorTemplate,
    get_phase3_template,
    iter_phase3_templates,
    phase3_catalog_addon_lines,
)

__all__ = [
    "PHASE3_TEMPLATE_INDEX",
    "Phase3ConnectorTemplate",
    "get_phase3_template",
    "iter_phase3_templates",
    "phase3_catalog_addon_lines",
]
