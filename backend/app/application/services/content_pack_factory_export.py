"""Content Pack Factory export bundle — ZIP-ready file list for operators."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.application.services.content_pack_factory_listing import (
    build_content_pack_listing_md,
    listing_context_from_pack_and_opportunity,
)
from app.application.services.publish_pack import build_publish_pack_markdown
from app.infrastructure.persistence.models.content_pack_opportunity import ContentPackOpportunityORM
from app.infrastructure.persistence.models.tenant_content_pack import TenantContentPackORM


class ContentPackExportFile(BaseModel):
    """One file in an export bundle."""

    model_config = ConfigDict(extra="forbid")

    path: str
    content: str


class ContentPackExportMeta(BaseModel):
    """Metadata for one content pack export."""

    model_config = ConfigDict(extra="ignore")

    pack_id: uuid.UUID
    slug: str
    title: str
    channel: str
    verified: bool
    verified_at: datetime | None
    price_eur_cents: int = 1900
    niche: str = ""


class ContentPackExportResponse(BaseModel):
    """Full export payload returned by API."""

    model_config = ConfigDict(extra="ignore")

    meta: ContentPackExportMeta
    files: list[ContentPackExportFile] = Field(default_factory=list)


def build_content_pack_export_bundle(
    pack: TenantContentPackORM,
    *,
    opportunity: ContentPackOpportunityORM | None = None,
) -> ContentPackExportResponse:
    """Assemble Gumroad-ready export bundle for one tenant content pack."""

    slug = pack.slug
    folder = slug
    ctx = listing_context_from_pack_and_opportunity(pack, opportunity)
    listing_md = pack.listing_markdown.strip() or build_content_pack_listing_md(
        pack=pack,
        slug=slug,
        ctx=ctx,
    )

    payload = dict(pack.pack_payload or {})
    pack_json = json.dumps(payload, indent=2, sort_keys=True)

    from app.application.services.publish_pack import PublishPackArtifact

    pack_md = ""
    try:
        artifact = PublishPackArtifact.model_validate(payload)
        pack_md = build_publish_pack_markdown(artifact)
    except Exception:
        pack_md = f"# {pack.title}\n\n{pack.description}\n"

    meta_json = json.dumps(
        {
            "slug": slug,
            "version": pack.version,
            "source": pack.source,
            "channel": pack.channel,
            "keywords": list(pack.keywords or []),
            "price_eur_cents": ctx.price_cents,
            "niche": ctx.niche,
            "simulate_only": True,
        },
        indent=2,
        sort_keys=True,
    )

    readme = "\n".join(
        [
            f"# {pack.title}",
            "",
            "Gumroad-ready content pack export from Queenswarm Content Pack Factory.",
            "",
            "## Files",
            "- `publish_pack.json` — validated simulate-first artifact",
            "- `PACK.md` — human-readable preview",
            "- `LISTING.md` — paste-ready Gumroad listing copy",
            "- `meta.json` — pricing and channel metadata",
            "",
            "## Safety",
            "All packs are simulate-only until operator publishes externally.",
            "",
        ],
    )

    files = [
        ContentPackExportFile(path=f"{folder}/publish_pack.json", content=pack_json + "\n"),
        ContentPackExportFile(path=f"{folder}/PACK.md", content=pack_md),
        ContentPackExportFile(path=f"{folder}/LISTING.md", content=listing_md),
        ContentPackExportFile(path=f"{folder}/meta.json", content=meta_json + "\n"),
        ContentPackExportFile(path=f"{folder}/README.md", content=readme),
    ]

    meta = ContentPackExportMeta(
        pack_id=pack.id,
        slug=slug,
        title=pack.title,
        channel=pack.channel,
        verified=pack.verified_at is not None,
        verified_at=pack.verified_at,
        price_eur_cents=ctx.price_cents,
        niche=ctx.niche,
    )
    return ContentPackExportResponse(meta=meta, files=files)


def export_response_to_dict(response: ContentPackExportResponse) -> dict[str, Any]:
    """Serialize export response for JSON API."""

    return {
        "meta": response.meta.model_dump(mode="json"),
        "files": [item.model_dump() for item in response.files],
    }


__all__ = [
    "ContentPackExportFile",
    "ContentPackExportMeta",
    "ContentPackExportResponse",
    "build_content_pack_export_bundle",
    "export_response_to_dict",
]
