"""Track O TJ7 — Journal Studio presets (trading vs business brain / Moneta notes)."""

from __future__ import annotations

from typing import Any, Literal

StudioPreset = Literal["trading", "business_brain"]

TRADING_FIELD_TOGGLES: dict[str, bool] = {
    "thesis": True,
    "setup": True,
    "entry_price": True,
    "exit_price": True,
    "position_size": True,
    "outcome": True,
    "pnl": True,
    "emotion": True,
    "screenshot": False,
    "lesson": True,
    "tags": True,
    "mistake_tag": True,
}

BUSINESS_BRAIN_FIELD_TOGGLES: dict[str, bool] = {
    "thesis": True,
    "setup": True,
    "entry_price": False,
    "exit_price": False,
    "position_size": False,
    "outcome": True,
    "pnl": False,
    "emotion": True,
    "screenshot": False,
    "lesson": True,
    "tags": True,
    "mistake_tag": True,
}

TRADING_FIELD_LABELS: dict[str, str] = {
    "thesis": "Thesis",
    "setup": "Setup",
    "entry_price": "Entry price",
    "exit_price": "Exit price",
    "position_size": "Position size",
    "outcome": "Outcome",
    "pnl": "P&L",
    "emotion": "Emotion",
    "screenshot": "Screenshot",
    "lesson": "Lesson learned",
    "tags": "Tags",
    "mistake_tag": "Mistake tag",
}

BUSINESS_BRAIN_FIELD_LABELS: dict[str, str] = {
    "thesis": "Hypothesis",
    "setup": "Campaign / context",
    "entry_price": "Entry price",
    "exit_price": "Exit price",
    "position_size": "Position size",
    "outcome": "Outcome",
    "pnl": "P&L",
    "emotion": "Stakeholder tone",
    "screenshot": "Screenshot",
    "lesson": "Lesson / next step",
    "tags": "Tags",
    "mistake_tag": "Pattern tag",
}

TRADING_MISTAKE_TAGS: list[str] = [
    "fomo",
    "revenge_trade",
    "no_stop",
    "oversized",
    "early_exit",
    "late_entry",
    "ignored_plan",
    "chased_price",
]

BUSINESS_BRAIN_PATTERN_TAGS: list[str] = [
    "scope_creep",
    "weak_kpi",
    "no_source",
    "stakeholder_miss",
    "compliance_gap",
    "shallow_research",
    "unclear_audience",
    "premature_ship",
]

TRADING_GOAL_TEMPLATE = """\
Trading journal review (verify-first, operator approve before vault write).

Review recent paper fills and manual journal entries for this tenant:
1. Summarize what worked and repeat mistakes (use configured mistake tags).
2. Draft Obsidian-ready markdown for operator approval — never write vault without HITL.
3. Cross-link thesis brief (NP5) when available.
4. Tag entries for pattern strip (30d / 90d) — simulate export only.

Skills: trading-journal-playbook, self-review-loop, obsidian-export-playbook.
Save deliverable tagged journal-review. Operator approve before Obsidian sync.
""".strip()

BUSINESS_BRAIN_GOAL_TEMPLATE = """\
Business brain review (verify-first, operator approve before vault write).

Review recent business / Moneta journal notes and Wiki Layer captures:
1. Summarize hypotheses validated, KPI gaps, and repeat pattern tags.
2. Cross-link investment-product-brief (NP4) and second-brain captures when relevant.
3. Draft Obsidian-ready markdown for operator approval — never write vault without HITL.
4. Tag notes for pattern strip (30d / 90d) — simulate export only.

Skills: self-review-loop, obsidian-export-playbook, investment-product-brief.
Save deliverable tagged business-brain-review. Operator approve before Obsidian sync.
""".strip()

_PRESET_CATALOG: dict[StudioPreset, dict[str, Any]] = {
    "trading": {
        "module_title": "Trading Journal",
        "module_subtitle": "Learning Loop Studio — timeline, entries, gardener, pre-trade recall, pattern strip.",
        "routine_name": "Trading journal review",
        "obsidian_subfolder": "Trading/Journal",
        "field_toggles": TRADING_FIELD_TOGGLES,
        "field_labels": TRADING_FIELD_LABELS,
        "mistake_tags": TRADING_MISTAKE_TAGS,
        "pattern_tags_label": "Mistake tags",
        "recall_panel_label": "Pre-trade recall",
        "goal_template": TRADING_GOAL_TEMPLATE,
        "wiki_capture_href": "/knowledge?tab=wiki",
        "brief_dispatch_href": "/tasks?goal_preset=trading-thesis",
        "operator_hint": "Capture trades, run gardener, export Obsidian vault after approve.",
    },
    "business_brain": {
        "module_title": "Business Brain",
        "module_subtitle": "Moneta / marketing notes — same studio shell, NP4 brief + Wiki Layer capture.",
        "routine_name": "Business brain review",
        "obsidian_subfolder": "Business/Brain",
        "field_toggles": BUSINESS_BRAIN_FIELD_TOGGLES,
        "field_labels": BUSINESS_BRAIN_FIELD_LABELS,
        "mistake_tags": BUSINESS_BRAIN_PATTERN_TAGS,
        "pattern_tags_label": "Pattern tags",
        "recall_panel_label": "Pre-session recall",
        "goal_template": BUSINESS_BRAIN_GOAL_TEMPLATE,
        "wiki_capture_href": "/knowledge?tab=wiki",
        "brief_dispatch_href": "/tasks?goal_preset=investment-product-brief",
        "operator_hint": "Log hypotheses, link NP4 brief, approve captures in Wiki Layer before export.",
    },
}


def normalize_studio_preset(raw: object) -> StudioPreset:
    """Coerce stored preset value."""

    text = str(raw or "trading").strip().lower()
    if text == "business_brain":
        return "business_brain"
    return "trading"


def get_preset_definition(preset: StudioPreset) -> dict[str, Any]:
    """Return preset catalog entry."""

    return dict(_PRESET_CATALOG[preset])


def preset_field_toggles(preset: StudioPreset) -> dict[str, bool]:
    """Default field toggles for preset."""

    return dict(get_preset_definition(preset)["field_toggles"])


def preset_mistake_tags(preset: StudioPreset) -> list[str]:
    """Default pattern/mistake tags for preset."""

    return list(get_preset_definition(preset)["mistake_tags"])


def preset_meta(preset: StudioPreset) -> dict[str, Any]:
    """UI metadata for active preset."""

    row = get_preset_definition(preset)
    return {
        "studio_preset": preset,
        "module_title": row["module_title"],
        "module_subtitle": row["module_subtitle"],
        "field_labels": dict(row["field_labels"]),
        "pattern_tags_label": row["pattern_tags_label"],
        "recall_panel_label": row["recall_panel_label"],
        "wiki_capture_href": row["wiki_capture_href"],
        "brief_dispatch_href": row["brief_dispatch_href"],
        "operator_hint": row["operator_hint"],
    }


__all__ = [
    "BUSINESS_BRAIN_FIELD_TOGGLES",
    "BUSINESS_BRAIN_PATTERN_TAGS",
    "StudioPreset",
    "TRADING_FIELD_TOGGLES",
    "get_preset_definition",
    "normalize_studio_preset",
    "preset_field_toggles",
    "preset_meta",
    "preset_mistake_tags",
]
