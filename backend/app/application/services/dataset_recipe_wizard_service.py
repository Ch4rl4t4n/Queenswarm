"""Track M LOC6 — Dataset Recipe wizard (PDF/CSV → Q&A via local model, HITL)."""

from __future__ import annotations

import csv
import io
import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.llm_routing import load_routing_config
from app.application.services.local_adapter_registry_service import list_tenant_local_adapter_slugs
from app.application.services.local_inference import resolve_ollama_model_slug
from app.application.services.verified_dataset_export_service import (
    VerifiedDatasetRowOut,
    build_verified_dataset_jsonl_bytes,
    redact_secrets,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

DATASET_RECIPE_SETTINGS_KEY = "dataset_recipe_wizard"
DatasetSourceKind = Literal["csv", "pdf", "text"]
DatasetRecipeStatus = Literal["empty", "parsed", "draft", "approved"]

_CHUNK_CHARS = 1800
_QA_JSON_PATTERN = re.compile(r"\[[\s\S]*\]")


class DatasetRecipePairOut(BaseModel):
    """One draft or approved Q&A row."""

    model_config = ConfigDict(extra="forbid")

    instruction: str
    input: str
    output: str
    approved: bool = False
    source_chunk: int = 0


class DatasetRecipeSnapshotOut(BaseModel):
    """Operator snapshot for dataset recipe wizard."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    local_only: bool
    local_model_slug: str
    status: DatasetRecipeStatus = "empty"
    source_filename: str | None = None
    source_kind: DatasetSourceKind | None = None
    chunk_count: int = 0
    draft_pair_count: int = 0
    approved_pair_count: int = 0
    draft_pairs: list[DatasetRecipePairOut] = Field(default_factory=list)
    operator_hint: str = ""


class DatasetRecipeParseOut(BaseModel):
    """Result of parsing an uploaded document."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    source_filename: str
    source_kind: DatasetSourceKind
    chunk_count: int
    preview_text: str
    message: str = ""


class DatasetRecipeGenerateOut(BaseModel):
    """Result of local LLM Q&A generation."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    model_slug: str
    pair_count: int
    draft_pairs: list[DatasetRecipePairOut] = Field(default_factory=list)
    message: str = ""


class DatasetRecipeApproveIn(BaseModel):
    """HITL approval — indices of draft pairs to export."""

    model_config = ConfigDict(extra="forbid")

    approved_indices: list[int] = Field(default_factory=list)

    @field_validator("approved_indices")
    @classmethod
    def _dedupe_indices(cls, value: list[int]) -> list[int]:
        return sorted({int(i) for i in value if int(i) >= 0})


def _bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    raw = operator_settings if isinstance(operator_settings, dict) else {}
    bucket = raw.get(DATASET_RECIPE_SETTINGS_KEY)
    return dict(bucket) if isinstance(bucket, dict) else {}


def _save_bucket(tenant: Tenant, bucket: dict[str, Any]) -> None:
    settings_map = dict(tenant.operator_settings or {})
    settings_map[DATASET_RECIPE_SETTINGS_KEY] = bucket
    tenant.operator_settings = settings_map


def _chunk_text(text: str, *, max_chars: int = _CHUNK_CHARS) -> list[str]:
    """Split document text into LLM-sized chunks."""

    cleaned = text.strip()
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + max_chars, len(cleaned))
        if end < len(cleaned):
            split_at = cleaned.rfind("\n\n", start, end)
            if split_at > start + 400:
                end = split_at
        chunks.append(cleaned[start:end].strip())
        start = end
    return [c for c in chunks if c]


def parse_csv_bytes(content: bytes) -> tuple[list[str], list[DatasetRecipePairOut]]:
    """Parse CSV — direct Q/A columns or fallback to text chunks."""

    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return _chunk_text(text), []

    lowered = {h.lower().strip(): h for h in reader.fieldnames if h}
    q_key = next((lowered[k] for k in ("question", "input", "prompt", "instruction") if k in lowered), None)
    a_key = next((lowered[k] for k in ("answer", "output", "response") if k in lowered), None)

    pairs: list[DatasetRecipePairOut] = []
    if q_key and a_key:
        instruction = "Answer the operator question using only the provided business context."
        for idx, row in enumerate(reader):
            question = str(row.get(q_key) or "").strip()
            answer = str(row.get(a_key) or "").strip()
            if not question or not answer:
                continue
            pairs.append(
                DatasetRecipePairOut(
                    instruction=instruction,
                    input=redact_secrets(question),
                    output=redact_secrets(answer),
                    source_chunk=idx,
                ),
            )
        if pairs:
            return [], pairs

    return _chunk_text(text), []


def parse_pdf_bytes(content: bytes) -> list[str]:
    """Extract text from PDF bytes."""

    try:
        from pypdf import PdfReader
    except ImportError as exc:
        msg = "PDF support requires pypdf — install backend requirements."
        raise RuntimeError(msg) from exc

    reader = PdfReader(io.BytesIO(content))
    pages: list[str] = []
    for page in reader.pages[: settings.dataset_recipe_max_pdf_pages]:
        extracted = page.extract_text() or ""
        if extracted.strip():
            pages.append(extracted.strip())
    return _chunk_text("\n\n".join(pages))


def parse_upload_bytes(*, filename: str, content: bytes) -> tuple[DatasetSourceKind, list[str], list[DatasetRecipePairOut]]:
    """Parse uploaded file into chunks and optional direct Q&A pairs."""

    if len(content) > settings.dataset_recipe_max_file_bytes:
        msg = f"File exceeds {settings.dataset_recipe_max_file_bytes} bytes."
        raise ValueError(msg)

    lowered = filename.lower()
    if lowered.endswith(".csv"):
        chunks, pairs = parse_csv_bytes(content)
        return "csv", chunks, pairs
    if lowered.endswith(".pdf"):
        return "pdf", parse_pdf_bytes(content), []
    if lowered.endswith((".txt", ".md", ".markdown")):
        text = content.decode("utf-8", errors="replace")
        return "text", _chunk_text(text), []

    msg = "Supported formats: .csv, .pdf, .txt, .md"
    raise ValueError(msg)


async def resolve_dataset_recipe_model_slug(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> str:
    """Resolve local-only model slug for dataset recipe generation."""

    if not settings.local_llm_enabled:
        msg = "Local LLM disabled on deployment."
        raise RuntimeError(msg)

    adapter_slugs = await list_tenant_local_adapter_slugs(session, tenant_id=tenant_id)
    active_adapter = adapter_slugs[0] if adapter_slugs else None

    if settings.llm_airgap:
        return active_adapter or resolve_ollama_model_slug()

    cfg = await load_routing_config(session, tenant_id=tenant_id)
    routing_mode = str(cfg.get("routing_mode") or "")
    if routing_mode == "local_sovereign":
        return active_adapter or resolve_ollama_model_slug()

    if settings.dataset_recipe_local_only:
        msg = (
            "Dataset Recipe wizard requires local_sovereign routing or LLM_AIRGAP=1 — "
            "cloud teacher calls are blocked by default."
        )
        raise RuntimeError(msg)

    return active_adapter or resolve_ollama_model_slug()


def _pairs_from_llm_json(raw: str) -> list[DatasetRecipePairOut]:
    """Parse LLM JSON array of Q&A objects."""

    match = _QA_JSON_PATTERN.search(raw)
    if not match:
        return []
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []

    pairs: list[DatasetRecipePairOut] = []
    instruction_default = (
        "You are a domain assistant. Answer using only the provided source excerpt — no speculation."
    )
    for item in payload[: settings.dataset_recipe_max_pairs_per_chunk]:
        if not isinstance(item, dict):
            continue
        inp = str(item.get("input") or item.get("question") or "").strip()
        out = str(item.get("output") or item.get("answer") or "").strip()
        if not inp or not out:
            continue
        inst = str(item.get("instruction") or instruction_default).strip()
        pairs.append(
            DatasetRecipePairOut(
                instruction=redact_secrets(inst),
                input=redact_secrets(inp),
                output=redact_secrets(out),
            ),
        )
    return pairs


async def generate_qa_pairs_for_chunks(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    chunks: list[str],
) -> tuple[str, list[DatasetRecipePairOut]]:
    """Generate Q&A pairs from text chunks using local model only."""

    from app.core.llm_router import LiteLLMRouter

    model_slug = await resolve_dataset_recipe_model_slug(session, tenant_id=tenant_id)
    router = LiteLLMRouter()
    all_pairs: list[DatasetRecipePairOut] = []
    cap = min(len(chunks), settings.dataset_recipe_max_chunks)

    for idx, chunk in enumerate(chunks[:cap]):
        messages = [
            {
                "role": "system",
                "content": (
                    "Generate Alpaca-style Q&A pairs from the source excerpt. "
                    f"Return JSON array only (max {settings.dataset_recipe_max_pairs_per_chunk} items): "
                    '[{"instruction":"...","input":"...","output":"..."}]'
                ),
            },
            {"role": "user", "content": chunk[: settings.dataset_recipe_max_chunk_chars]},
        ]
        content, _cost = await router.complete_single_model(
            session,
            model_name=model_slug,
            messages=messages,
            max_tokens=1200,
            temperature=0.2,
            task_id=f"dataset-recipe-{idx}",
        )
        chunk_pairs = _pairs_from_llm_json(content)
        for pair in chunk_pairs:
            pair.source_chunk = idx
            all_pairs.append(pair)

    return model_slug, all_pairs


def compose_snapshot_from_bucket(*, bucket: dict[str, Any], local_model_slug: str) -> DatasetRecipeSnapshotOut:
    """Build UI snapshot from tenant settings bucket."""

    enabled = settings.local_llm_enabled and settings.dataset_recipe_wizard_enabled
    raw_pairs = bucket.get("draft_pairs") if isinstance(bucket.get("draft_pairs"), list) else []
    pairs: list[DatasetRecipePairOut] = []
    for item in raw_pairs:
        if isinstance(item, dict):
            pairs.append(DatasetRecipePairOut.model_validate(item))

    approved_count = sum(1 for p in pairs if p.approved)
    status: DatasetRecipeStatus = "empty"
    if bucket.get("status") == "approved" and approved_count > 0:
        status = "approved"
    elif pairs:
        status = "draft"
    elif bucket.get("chunk_count"):
        status = "parsed"

    return DatasetRecipeSnapshotOut(
        enabled=enabled,
        local_only=settings.dataset_recipe_local_only,
        local_model_slug=local_model_slug,
        status=status,
        source_filename=bucket.get("source_filename"),
        source_kind=bucket.get("source_kind"),
        chunk_count=int(bucket.get("chunk_count") or 0),
        draft_pair_count=len(pairs),
        approved_pair_count=approved_count,
        draft_pairs=pairs[:20],
        operator_hint=(
            "Upload CSV/PDF/text → Generate Q&A (local model) → Approve rows → Export JSONL for Unsloth."
            if enabled
            else "Enable LOCAL_LLM_ENABLED and dataset_recipe_wizard."
        ),
    )


async def compose_dataset_recipe_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    tenant: Tenant,
) -> DatasetRecipeSnapshotOut:
    """Return wizard snapshot for Settings UI."""

    try:
        slug = await resolve_dataset_recipe_model_slug(session, tenant_id=tenant_id)
    except RuntimeError:
        slug = resolve_ollama_model_slug()
    return compose_snapshot_from_bucket(bucket=_bucket(tenant.operator_settings), local_model_slug=slug)


async def parse_and_store_upload(
    session: AsyncSession,
    *,
    tenant: Tenant,
    filename: str,
    content: bytes,
) -> DatasetRecipeParseOut:
    """Parse upload and persist chunks in tenant settings."""

    kind, chunks, direct_pairs = parse_upload_bytes(filename=filename, content=content)
    bucket = _bucket(tenant.operator_settings)
    bucket.update(
        {
            "source_filename": filename,
            "source_kind": kind,
            "chunk_count": len(chunks),
            "chunks": chunks[: settings.dataset_recipe_max_chunks],
            "draft_pairs": [p.model_dump(mode="json") for p in direct_pairs],
            "status": "parsed" if direct_pairs else "parsed",
            "parsed_at": datetime.now(tz=UTC).isoformat(),
        },
    )
    _save_bucket(tenant, bucket)
    await session.commit()

    preview = (direct_pairs[0].input if direct_pairs else (chunks[0] if chunks else ""))[:400]
    return DatasetRecipeParseOut(
        ok=True,
        source_filename=filename,
        source_kind=kind,
        chunk_count=len(chunks) if chunks else len(direct_pairs),
        preview_text=preview,
        message=(
            f"Parsed {len(direct_pairs)} direct Q&A row(s) from CSV."
            if direct_pairs
            else f"Parsed {len(chunks)} chunk(s) — run Generate for local Q&A."
        ),
    )


async def generate_dataset_recipe_draft(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    tenant: Tenant,
) -> DatasetRecipeGenerateOut:
    """Run local LLM Q&A generation on stored chunks."""

    bucket = _bucket(tenant.operator_settings)
    chunks = [str(c) for c in bucket.get("chunks") or [] if str(c).strip()]
    existing = bucket.get("draft_pairs") if isinstance(bucket.get("draft_pairs"), list) else []
    if existing and not chunks:
        pairs = [DatasetRecipePairOut.model_validate(item) for item in existing if isinstance(item, dict)]
        return DatasetRecipeGenerateOut(
            ok=True,
            model_slug=resolve_ollama_model_slug(),
            pair_count=len(pairs),
            draft_pairs=pairs,
            message="Using direct CSV Q&A rows — approve before export.",
        )

    if not chunks:
        return DatasetRecipeGenerateOut(ok=False, model_slug="", pair_count=0, message="Parse a document first.")

    model_slug, pairs = await generate_qa_pairs_for_chunks(session, tenant_id=tenant_id, chunks=chunks)
    if not pairs:
        return DatasetRecipeGenerateOut(
            ok=False,
            model_slug=model_slug,
            pair_count=0,
            message="Local model returned no valid Q&A pairs — try a smaller excerpt.",
        )

    bucket["draft_pairs"] = [p.model_dump(mode="json") for p in pairs]
    bucket["status"] = "draft"
    bucket["model_slug"] = model_slug
    bucket["generated_at"] = datetime.now(tz=UTC).isoformat()
    _save_bucket(tenant, bucket)
    await session.commit()

    _logger.info(
        "dataset_recipe_wizard.generated",
        tenant_id=str(tenant_id),
        pair_count=len(pairs),
        model_slug=model_slug,
    )
    return DatasetRecipeGenerateOut(
        ok=True,
        model_slug=model_slug,
        pair_count=len(pairs),
        draft_pairs=pairs[:20],
        message=f"Generated {len(pairs)} draft Q&A pair(s) via {model_slug}.",
    )


async def approve_dataset_recipe_pairs(
    session: AsyncSession,
    *,
    tenant: Tenant,
    payload: DatasetRecipeApproveIn,
) -> DatasetRecipeSnapshotOut:
    """HITL — mark selected draft pairs as approved."""

    bucket = _bucket(tenant.operator_settings)
    raw_pairs = bucket.get("draft_pairs") if isinstance(bucket.get("draft_pairs"), list) else []
    pairs: list[DatasetRecipePairOut] = []
    for item in raw_pairs:
        if isinstance(item, dict):
            pairs.append(DatasetRecipePairOut.model_validate(item))

    if not pairs:
        msg = "No draft pairs to approve."
        raise ValueError(msg)

    approved_set = set(payload.approved_indices)
    if not approved_set:
        approved_set = set(range(len(pairs)))

    for idx, pair in enumerate(pairs):
        pair.approved = idx in approved_set

    bucket["draft_pairs"] = [p.model_dump(mode="json") for p in pairs]
    bucket["status"] = "approved"
    bucket["approved_at"] = datetime.now(tz=UTC).isoformat()
    _save_bucket(tenant, bucket)
    await session.commit()

    slug = str(bucket.get("model_slug") or resolve_ollama_model_slug())
    return compose_snapshot_from_bucket(bucket=bucket, local_model_slug=slug)


def export_approved_dataset_recipe_jsonl(tenant: Tenant) -> tuple[bytes, int]:
    """Export HITL-approved pairs as Alpaca JSONL."""

    bucket = _bucket(tenant.operator_settings)
    raw_pairs = bucket.get("draft_pairs") if isinstance(bucket.get("draft_pairs"), list) else []
    rows: list[VerifiedDatasetRowOut] = []
    for idx, item in enumerate(raw_pairs):
        if not isinstance(item, dict):
            continue
        pair = DatasetRecipePairOut.model_validate(item)
        if not pair.approved:
            continue
        rows.append(
            VerifiedDatasetRowOut(
                instruction=pair.instruction,
                input=pair.input,
                output=pair.output,
                source_type="recipe",
                source_id=f"dataset-recipe-{idx}",
                source_label=str(bucket.get("source_filename") or "dataset-recipe"),
            ),
        )

    if not rows:
        msg = "No approved pairs — run Generate then Approve."
        raise ValueError(msg)

    return build_verified_dataset_jsonl_bytes(rows), len(rows)


__all__ = [
    "DatasetRecipeApproveIn",
    "DatasetRecipeGenerateOut",
    "DatasetRecipePairOut",
    "DatasetRecipeParseOut",
    "DatasetRecipeSnapshotOut",
    "approve_dataset_recipe_pairs",
    "compose_dataset_recipe_snapshot",
    "export_approved_dataset_recipe_jsonl",
    "generate_dataset_recipe_draft",
    "parse_and_store_upload",
    "parse_upload_bytes",
]
