"""NP3 — Brand Context Pack: voice, claims, visual refs, examples for marketing sessions."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.curated_memory_service import CuratedMemoryService
from app.core.config import settings
from app.core.logging import get_logger
from app.domain.memory.curated import CuratedFileKind
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

BRAND_SECTION_VOICE = "voice bullets"
BRAND_SECTION_FORBIDDEN = "forbidden claims"
BRAND_SECTION_VISUAL = "visual identity"
BRAND_SECTION_EXAMPLES = "example posts"
BRAND_SECTION_COMPETITOR = "competitor tone notes"

_RE_SECTION = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_RE_URL = re.compile(r"https?://[^\s)>\"]+", re.IGNORECASE)
_MIN_VOICE_CHARS = 20
_MIN_FORBIDDEN_CHARS = 10
_MIN_EXAMPLE_CHARS = 20


class BrandSectionOut(BaseModel):
    """One parsed brand pack section."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    content: str
    char_count: int
    filled: bool


class BrandContextPackSnapshotOut(BaseModel):
    """Snapshot for Brain Pack Brand tab and solo-operator API."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    ready: bool = False
    char_count: int = 0
    max_chars: int = Field(default=16_000, ge=1)
    injection_max_chars: int = Field(default=1300, ge=1)
    usage_pct: int = Field(default=0, ge=0, le=100)
    sections: list[BrandSectionOut] = Field(default_factory=list)
    marketing_injection_preview: str = ""
    href: str = "/knowledge?tab=memory#brain-pack-brand"


def _section_specs() -> tuple[tuple[str, str], ...]:
    return (
        ("voice", BRAND_SECTION_VOICE.title()),
        ("forbidden", BRAND_SECTION_FORBIDDEN.title()),
        ("visual", f"{BRAND_SECTION_VISUAL.title()} (URLs only)"),
        ("examples", BRAND_SECTION_EXAMPLES.title()),
        ("competitor", BRAND_SECTION_COMPETITOR.title()),
    )


def parse_brand_sections(content_md: str) -> dict[str, str]:
    """Parse ## headings into section id → body map."""

    text = (content_md or "").strip()
    if not text:
        return {}

    matches = list(_RE_SECTION.finditer(text))
    if not matches:
        return {"voice": text}

    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        heading = match.group(1).strip().lower()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        section_id = _heading_to_id(heading)
        if section_id:
            sections[section_id] = body
    return sections


def _heading_to_id(heading: str) -> str | None:
    normalized = heading.lower()
    if "voice" in normalized:
        return "voice"
    if "forbidden" in normalized:
        return "forbidden"
    if "visual" in normalized or "logo" in normalized or "hex" in normalized:
        return "visual"
    if "example" in normalized:
        return "examples"
    if "competitor" in normalized:
        return "competitor"
    return None


def is_brand_pack_ready(content_md: str) -> bool:
    """Return True when voice, forbidden claims, and one example are filled."""

    sections = parse_brand_sections(content_md)
    voice = (sections.get("voice") or "").strip()
    forbidden = (sections.get("forbidden") or "").strip()
    examples = (sections.get("examples") or "").strip()
    return (
        len(voice) >= _MIN_VOICE_CHARS
        and len(forbidden) >= _MIN_FORBIDDEN_CHARS
        and len(examples) >= _MIN_EXAMPLE_CHARS
    )


def _truncate_injection(text: str, *, max_chars: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return f"{cleaned[: max_chars - 1].rstrip()}…"


def render_marketing_brand_injection(content_md: str, *, max_chars: int | None = None) -> str:
    """Render capped brand block for marketing harness sessions only."""

    if not (content_md or "").strip():
        return ""
    cap = max_chars if max_chars is not None else int(settings.brand_context_max_injection_chars)
    body = _truncate_injection(content_md, max_chars=cap)
    if not body:
        return ""
    return (
        "=== BRAND CONTEXT PACK (marketing harness only) ===\n"
        f"{body}\n"
        "=== END BRAND CONTEXT ==="
    )


def compose_brand_sections_view(content_md: str) -> list[BrandSectionOut]:
    """Build UI section rows from markdown."""

    parsed = parse_brand_sections(content_md)
    rows: list[BrandSectionOut] = []
    for section_id, label in _section_specs():
        content = (parsed.get(section_id) or "").strip()
        min_chars = {
            "voice": _MIN_VOICE_CHARS,
            "forbidden": _MIN_FORBIDDEN_CHARS,
            "examples": _MIN_EXAMPLE_CHARS,
        }.get(section_id, 8)
        rows.append(
            BrandSectionOut(
                id=section_id,
                label=label,
                content=content,
                char_count=len(content),
                filled=len(content) >= min_chars,
            ),
        )
    return rows


async def compose_brand_context_pack_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> BrandContextPackSnapshotOut:
    """Return brand pack readiness, sections, and injection preview."""

    if not settings.brand_context_pack_enabled:
        return BrandContextPackSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            max_chars=CuratedMemoryService.max_chars_per_file(),
            injection_max_chars=int(settings.brand_context_max_injection_chars),
        )

    memory = CuratedMemoryService(db=session)
    bundle = await memory.get_bundle(tenant_id)
    brand_md = (bundle.get(CuratedFileKind.BRAND) or "").strip()
    max_file = CuratedMemoryService.max_chars_per_file()
    char_count = len(brand_md)
    usage_pct = min(100, round((char_count / max_file) * 100)) if max_file else 0
    preview = render_marketing_brand_injection(brand_md)

    return BrandContextPackSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        ready=is_brand_pack_ready(brand_md),
        char_count=char_count,
        max_chars=max_file,
        injection_max_chars=int(settings.brand_context_max_injection_chars),
        usage_pct=usage_pct,
        sections=compose_brand_sections_view(brand_md),
        marketing_injection_preview=preview[:500],
    )


async def should_inject_brand_for_session(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    context_seed: dict[str, object] | None,
) -> bool:
    """Return True when marketing harness profile is active for this session."""

    if not settings.brand_context_pack_enabled:
        return False

    seed = dict(context_seed or {})
    profile_id = str(seed.get("harness_profile_id") or seed.get("harness_profile") or "").strip()
    if profile_id == "marketing":
        return True
    if bool(seed.get("marketing_harness")):
        return True

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        return False

    from app.application.services.harness_project_profiles import get_active_harness_profile

    active = get_active_harness_profile(tenant)
    return active.profile_id == "marketing"


async def load_marketing_brand_injection(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    context_seed: dict[str, object] | None,
) -> str:
    """Load brand injection block when marketing profile applies."""

    if not await should_inject_brand_for_session(session, tenant_id=tenant_id, context_seed=context_seed):
        return ""

    memory = CuratedMemoryService(db=session)
    bundle = await memory.get_bundle(tenant_id)
    brand_md = bundle.get(CuratedFileKind.BRAND, "")
    block = render_marketing_brand_injection(brand_md)
    if block:
        _logger.debug(
            "brand_context_pack.injected",
            agent_id="brand_context_pack",
            swarm_id=str(tenant_id),
            chars=len(block),
        )
    return block


__all__ = [
    "BrandContextPackSnapshotOut",
    "BrandSectionOut",
    "compose_brand_context_pack_snapshot",
    "is_brand_pack_ready",
    "load_marketing_brand_injection",
    "parse_brand_sections",
    "render_marketing_brand_injection",
    "should_inject_brand_for_session",
]
