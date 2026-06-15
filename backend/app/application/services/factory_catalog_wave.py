"""Track MK6 — Factory catalog wave planner (16 → 25 → 50+ scorecard-clean listings)."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.application.services.factory_vertical_seeds import (
    CONTENT_PACK_VERTICAL_SEEDS,
    SKILL_FACTORY_VERTICAL_SEEDS,
)
from app.application.services.marketing_product_catalog import (
    _normalize_family_key,
    build_catalog,
    collect_catalog_products,
)

WAVE_TARGETS: dict[str, int] = {
    "wave_0": 16,
    "wave_1": 25,
    "wave_2": 50,
}

MK6_TARGET_LISTINGS = WAVE_TARGETS["wave_2"]


class FactoryWaveProgressRow(BaseModel):
    """Progress for one catalog wave."""

    model_config = ConfigDict(extra="ignore")

    wave_id: str
    label: str
    target: int
    scorecard_clean: int
    catalog_deduped: int
    complete: bool


class FactoryCatalogWaveOut(BaseModel):
    """MK6 operator + marketing wave status."""

    model_config = ConfigDict(extra="ignore")

    current_wave: str
    target_next: int
    mk6_target: int = MK6_TARGET_LISTINGS
    scorecard_ready_count: int = 0
    scorecard_total_count: int = 0
    scorecard_clean_count: int = 0
    catalog_deduped_count: int = 0
    gap_to_next_wave: int = 0
    gap_to_mk6: int = 0
    seed_total: int = 0
    seed_pending_count: int = 0
    pending_seeds_preview: list[str] = Field(default_factory=list)
    waves: list[FactoryWaveProgressRow] = Field(default_factory=list)
    next_operator_action: str = ""


def _resolve_export_root(export_root: Path | None = None) -> Path:
    if export_root is not None:
        return export_root.expanduser().resolve()
    candidates = (
        Path("exports"),
        Path(__file__).resolve().parents[4] / "exports",
        Path("/exports"),
        Path("/app/exports"),
    )
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if (resolved / "gumroad-ready").is_dir() or (resolved / "GUMROAD_SCORECARD.md").is_file():
            return resolved
    return Path("exports").resolve()


def _slugify_seed(seed: str) -> str:
    """Approximate catalog family key from a vertical seed phrase."""

    base = seed.lower().split("(")[0].strip()
    words = re.findall(r"[a-z0-9]+", base)
    return "-".join(words[:8])


def _catalog_family_keys(export_root: Path) -> set[str]:
    products = collect_catalog_products(export_root)
    return {_normalize_family_key(product.slug) for product in products}


def _seed_covered(seed: str, families: set[str]) -> bool:
    key = _slugify_seed(seed)
    if not key:
        return False
    seed_words = {word for word in key.split("-") if len(word) > 2}
    for family in families:
        if key in family or family in key:
            return True
        family_words = {word for word in family.split("-") if len(word) > 2}
        overlap = seed_words & family_words
        if len(overlap) >= 2:
            return True
    return False


def parse_scorecard_counts(scorecard_md: str) -> tuple[int, int, int]:
    """Return (ready_or_uploaded, total, scorecard_clean_100)."""

    total = 0
    ready = 0
    clean = 0
    header = re.search(r"Ready:\s+\*\*(\d+)/(\d+)\*\*", scorecard_md)
    if header:
        ready = int(header.group(1))
        total = int(header.group(2))
    for line in scorecard_md.splitlines():
        match = re.search(r"`([^`]+)`\s+—\s+(\d+)/100\s+(\w+)", line)
        if not match:
            continue
        score = int(match.group(2))
        verdict = match.group(3)
        if score >= 100 and verdict in {"ready", "uploaded"}:
            clean += 1
    if total == 0:
        product_lines = [line for line in scorecard_md.splitlines() if "`" in line and "/100" in line]
        total = len(product_lines)
    if clean == 0 and ready > 0:
        clean = ready
    return ready, total, clean


def pending_vertical_seeds(export_root: Path | None = None) -> list[str]:
    """Vertical seeds not yet represented in deduped catalog families."""

    root = _resolve_export_root(export_root)
    families = _catalog_family_keys(root)
    pending: list[str] = []
    for seed in (*SKILL_FACTORY_VERTICAL_SEEDS, *CONTENT_PACK_VERTICAL_SEEDS):
        if not _seed_covered(seed, families):
            pending.append(seed)
    return pending


def _current_wave_id(scorecard_clean: int) -> str:
    if scorecard_clean >= WAVE_TARGETS["wave_2"]:
        return "complete"
    if scorecard_clean >= WAVE_TARGETS["wave_1"]:
        return "wave_2"
    if scorecard_clean >= WAVE_TARGETS["wave_0"]:
        return "wave_1"
    return "wave_0"


def _target_for_wave(wave_id: str) -> int:
    if wave_id == "wave_0":
        return WAVE_TARGETS["wave_0"]
    if wave_id == "wave_1":
        return WAVE_TARGETS["wave_1"]
    if wave_id == "wave_2":
        return WAVE_TARGETS["wave_2"]
    return WAVE_TARGETS["wave_2"]


def build_factory_catalog_wave(export_root: Path | None = None) -> FactoryCatalogWaveOut:
    """Compose MK6 wave progress from scorecard + catalog + seed SSOT."""

    root = _resolve_export_root(export_root)
    scorecard_path = root / "GUMROAD_SCORECARD.md"
    scorecard_md = ""
    if scorecard_path.is_file():
        try:
            scorecard_md = scorecard_path.read_text(encoding="utf-8")
        except OSError:
            scorecard_md = ""

    ready, total, clean = parse_scorecard_counts(scorecard_md)
    catalog = build_catalog(root)
    catalog_count = catalog.product_count
    current = _current_wave_id(clean)
    target_next = _target_for_wave(current) if current != "complete" else WAVE_TARGETS["wave_2"]
    gap_next = max(0, target_next - clean)
    gap_mk6 = max(0, MK6_TARGET_LISTINGS - clean)

    pending = pending_vertical_seeds(root)
    seed_total = len(SKILL_FACTORY_VERTICAL_SEEDS) + len(CONTENT_PACK_VERTICAL_SEEDS)

    waves: list[FactoryWaveProgressRow] = []
    for wave_id, target in WAVE_TARGETS.items():
        label = wave_id.replace("_", " ").title()
        waves.append(
            FactoryWaveProgressRow(
                wave_id=wave_id,
                label=label,
                target=target,
                scorecard_clean=clean,
                catalog_deduped=catalog_count,
                complete=clean >= target,
            ),
        )

    if current == "complete":
        next_action = "MK6 target met — promote letagentscook.org and track conversions."
    elif gap_next > 0 and pending:
        next_action = (
            f"Run Skill + Content Pack Factory on {min(gap_next, len(pending))} pending seed(s) "
            f"→ gumroad_ready_package.py --all → scorecard gate."
        )
    elif gap_next > 0:
        next_action = "Expand factory_vertical_seeds or regenerate gumroad-ready packages."
    else:
        next_action = "Continue Gumroad upload and marketing promotion."

    return FactoryCatalogWaveOut(
        current_wave=current,
        target_next=target_next,
        scorecard_ready_count=ready,
        scorecard_total_count=total,
        scorecard_clean_count=clean,
        catalog_deduped_count=catalog_count,
        gap_to_next_wave=gap_next,
        gap_to_mk6=gap_mk6,
        seed_total=seed_total,
        seed_pending_count=len(pending),
        pending_seeds_preview=pending[:8],
        waves=waves,
        next_operator_action=next_action,
    )


__all__ = [
    "MK6_TARGET_LISTINGS",
    "WAVE_TARGETS",
    "FactoryCatalogWaveOut",
    "FactoryWaveProgressRow",
    "build_factory_catalog_wave",
    "parse_scorecard_counts",
    "pending_vertical_seeds",
]
