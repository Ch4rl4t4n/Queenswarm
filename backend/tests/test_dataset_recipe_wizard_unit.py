"""Unit tests for Track M LOC6 dataset recipe wizard."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.dataset_recipe_wizard_service import (
    DatasetRecipeApproveIn,
    approve_dataset_recipe_pairs,
    compose_dataset_recipe_snapshot,
    compose_snapshot_from_bucket,
    export_approved_dataset_recipe_jsonl,
    generate_dataset_recipe_draft,
    generate_qa_pairs_for_chunks,
    parse_csv_bytes,
    parse_upload_bytes,
    parse_and_store_upload,
    _chunk_text,
    _pairs_from_llm_json,
)
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant


def test_parse_csv_bytes_direct_qa_columns() -> None:
    csv_body = b"question,answer\nWhat is WAU?,12400 users\n"
    chunks, pairs = parse_csv_bytes(csv_body)
    assert chunks == []
    assert len(pairs) == 1
    assert "WAU" in pairs[0].input


def test_parse_csv_bytes_fallback_chunks() -> None:
    csv_body = b"metric,value\nwau,100\n"
    chunks, pairs = parse_csv_bytes(csv_body)
    assert len(chunks) >= 1
    assert pairs == []


def test_parse_upload_bytes_txt() -> None:
    kind, chunks, pairs = parse_upload_bytes(filename="notes.md", content=b"# Title\nBody text.")
    assert kind == "text"
    assert len(chunks) == 1
    assert pairs == []


def test_pairs_from_llm_json() -> None:
    raw = 'Here you go:\n[{"instruction":"A","input":"Q?","output":"Yes"}]\n'
    pairs = _pairs_from_llm_json(raw)
    assert len(pairs) == 1
    assert pairs[0].output == "Yes"


def test_pairs_from_llm_json_invalid_payload() -> None:
    assert _pairs_from_llm_json("no json here") == []
    assert _pairs_from_llm_json("[not valid json") == []
    assert _pairs_from_llm_json('{"not":"array"}') == []
    assert _pairs_from_llm_json('[{"input":"","output":"x"}]') == []


def test_chunk_text_empty_and_multipart() -> None:
    assert _chunk_text("") == []
    assert _chunk_text("short") == ["short"]
    long_body = ("paragraph one.\n\n" + ("word " * 400)).strip()
    chunks = _chunk_text(long_body, max_chars=500)
    assert len(chunks) >= 2


def test_parse_csv_bytes_skips_empty_rows() -> None:
    csv_body = b"question,answer\n,empty\nWhat?,Yes\n"
    chunks, pairs = parse_csv_bytes(csv_body)
    assert chunks == []
    assert len(pairs) == 1


def test_parse_upload_bytes_rejects_unknown_format() -> None:
    with pytest.raises(ValueError, match="Supported formats"):
        parse_upload_bytes(filename="data.xlsx", content=b"binary")


def test_parse_upload_bytes_rejects_oversized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "dataset_recipe_max_file_bytes", 10)
    with pytest.raises(ValueError, match="exceeds"):
        parse_upload_bytes(filename="big.txt", content=b"x" * 20)


def test_parse_upload_bytes_pdf_extension(monkeypatch: pytest.MonkeyPatch) -> None:
    with patch(
        "app.application.services.dataset_recipe_wizard_service.parse_pdf_bytes",
        return_value=["pdf chunk"],
    ):
        kind, chunks, pairs = parse_upload_bytes(filename="doc.pdf", content=b"%PDF")
    assert kind == "pdf"
    assert chunks == ["pdf chunk"]
    assert pairs == []


def test_compose_snapshot_from_bucket_approved_status() -> None:
    bucket = {
        "status": "approved",
        "draft_pairs": [
            {
                "instruction": "A",
                "input": "Q",
                "output": "O",
                "approved": True,
                "source_chunk": 0,
            },
        ],
    }
    snap = compose_snapshot_from_bucket(bucket=bucket, local_model_slug="ollama/qwen")
    assert snap.status == "approved"
    assert snap.approved_pair_count == 1


@pytest.mark.asyncio
async def test_parse_and_store_upload_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant = Tenant(id=uuid.uuid4(), name="t", slug="t", operator_settings={})
    session = AsyncMock()
    session.commit = AsyncMock()

    result = await parse_and_store_upload(
        session,
        tenant=tenant,
        filename="pairs.csv",
        content=b"question,answer\nQ1,A1\n",
    )
    assert result.ok is True
    assert result.source_kind == "csv"
    bucket = tenant.operator_settings.get("dataset_recipe_wizard") or {}
    assert len(bucket.get("draft_pairs") or []) == 1


@pytest.mark.asyncio
async def test_generate_dataset_recipe_draft_from_csv_direct(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant = Tenant(
        id=uuid.uuid4(),
        name="t",
        slug="t",
        operator_settings={
            "dataset_recipe_wizard": {
                "draft_pairs": [
                    {
                        "instruction": "A",
                        "input": "Q",
                        "output": "O",
                        "approved": False,
                        "source_chunk": 0,
                    },
                ],
                "chunks": [],
            },
        },
    )
    session = AsyncMock()
    out = await generate_dataset_recipe_draft(session, tenant_id=tenant.id, tenant=tenant)
    assert out.ok is True
    assert out.pair_count == 1


@pytest.mark.asyncio
async def test_generate_dataset_recipe_draft_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_llm_enabled", True)
    monkeypatch.setattr(settings, "llm_airgap", True)
    tenant = Tenant(
        id=uuid.uuid4(),
        name="t",
        slug="t",
        operator_settings={
            "dataset_recipe_wizard": {
                "chunks": ["Revenue grew 12% in Q1."],
            },
        },
    )
    session = AsyncMock()
    session.commit = AsyncMock()

    with patch(
        "app.application.services.dataset_recipe_wizard_service.generate_qa_pairs_for_chunks",
        new=AsyncMock(
            return_value=(
                "ollama/qwen2.5:7b",
                _pairs_from_llm_json('[{"input":"Q?","output":"12%"}]'),
            ),
        ),
    ):
        out = await generate_dataset_recipe_draft(session, tenant_id=tenant.id, tenant=tenant)
    assert out.ok is True
    assert out.pair_count == 1


@pytest.mark.asyncio
async def test_compose_dataset_recipe_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_llm_enabled", True)
    monkeypatch.setattr(settings, "dataset_recipe_wizard_enabled", True)
    monkeypatch.setattr(settings, "llm_airgap", True)
    tenant = Tenant(
        id=uuid.uuid4(),
        name="t",
        slug="t",
        operator_settings={"dataset_recipe_wizard": {"chunk_count": 2, "status": "parsed"}},
    )
    session = AsyncMock()
    with patch(
        "app.application.services.dataset_recipe_wizard_service.list_tenant_local_adapter_slugs",
        new=AsyncMock(return_value=[]),
    ):
        snap = await compose_dataset_recipe_snapshot(session, tenant_id=tenant.id, tenant=tenant)
    assert snap.enabled is True
    assert snap.chunk_count == 2


@pytest.mark.asyncio
async def test_resolve_dataset_recipe_model_slug_airgap(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.dataset_recipe_wizard_service import resolve_dataset_recipe_model_slug

    monkeypatch.setattr(settings, "local_llm_enabled", True)
    monkeypatch.setattr(settings, "llm_airgap", True)
    session = AsyncMock()
    with patch(
        "app.application.services.dataset_recipe_wizard_service.list_tenant_local_adapter_slugs",
        new=AsyncMock(return_value=[]),
    ):
        slug = await resolve_dataset_recipe_model_slug(session, tenant_id=uuid.uuid4())
    assert slug.startswith("ollama/")


def test_parse_pdf_bytes(tmp_path) -> None:
    from app.application.services.dataset_recipe_wizard_service import parse_pdf_bytes

    try:
        from fpdf import FPDF
    except ImportError:
        pytest.skip("fpdf2 not installed")

    try:
        from pypdf import PdfReader  # noqa: F401
    except ImportError:
        pytest.skip("pypdf not installed")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(text="Dataset recipe PDF sample.")
    out = tmp_path / "sample.pdf"
    pdf.output(str(out))
    chunks = parse_pdf_bytes(out.read_bytes())
    assert len(chunks) >= 1
    assert "Dataset recipe" in chunks[0]


@pytest.mark.asyncio
async def test_resolve_dataset_recipe_blocks_cloud_without_sovereign(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.dataset_recipe_wizard_service import resolve_dataset_recipe_model_slug

    monkeypatch.setattr(settings, "local_llm_enabled", True)
    monkeypatch.setattr(settings, "llm_airgap", False)
    monkeypatch.setattr(settings, "dataset_recipe_local_only", True)
    session = AsyncMock()
    with patch(
        "app.application.services.dataset_recipe_wizard_service.load_routing_config",
        new=AsyncMock(return_value={"routing_mode": "quality"}),
    ):
        with patch(
            "app.application.services.dataset_recipe_wizard_service.list_tenant_local_adapter_slugs",
            new=AsyncMock(return_value=[]),
        ):
            with pytest.raises(RuntimeError, match="local_sovereign"):
                await resolve_dataset_recipe_model_slug(session, tenant_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_approve_and_export_jsonl() -> None:
    tenant = Tenant(
        id=uuid.uuid4(),
        name="t",
        slug="t",
        operator_settings={
            "dataset_recipe_wizard": {
                "draft_pairs": [
                    {
                        "instruction": "A",
                        "input": "Q1",
                        "output": "O1",
                        "approved": False,
                        "source_chunk": 0,
                    },
                    {
                        "instruction": "A",
                        "input": "Q2",
                        "output": "O2",
                        "approved": False,
                        "source_chunk": 1,
                    },
                ],
            },
        },
    )
    session = AsyncMock()
    session.commit = AsyncMock()

    snap = await approve_dataset_recipe_pairs(
        session,
        tenant=tenant,
        payload=DatasetRecipeApproveIn(approved_indices=[0]),
    )
    assert snap.approved_pair_count == 1

    blob, count = export_approved_dataset_recipe_jsonl(tenant)
    assert count == 1
    assert b"Q1" in blob


@pytest.mark.asyncio
async def test_dataset_recipe_snapshot_requires_auth() -> None:
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/llm-routing/dataset-recipe")
    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_generate_dataset_recipe_draft_no_chunks() -> None:
    tenant = Tenant(id=uuid.uuid4(), name="t", slug="t", operator_settings={})
    session = AsyncMock()
    out = await generate_dataset_recipe_draft(session, tenant_id=tenant.id, tenant=tenant)
    assert out.ok is False
    assert "Parse a document" in out.message


@pytest.mark.asyncio
async def test_generate_dataset_recipe_draft_llm_empty_pairs(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant = Tenant(
        id=uuid.uuid4(),
        name="t",
        slug="t",
        operator_settings={"dataset_recipe_wizard": {"chunks": ["Some text"]}},
    )
    session = AsyncMock()
    with patch(
        "app.application.services.dataset_recipe_wizard_service.generate_qa_pairs_for_chunks",
        new=AsyncMock(return_value=("ollama/qwen", [])),
    ):
        out = await generate_dataset_recipe_draft(session, tenant_id=tenant.id, tenant=tenant)
    assert out.ok is False
    assert "no valid Q&A" in out.message


@pytest.mark.asyncio
async def test_generate_qa_pairs_for_chunks_calls_router(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_llm_enabled", True)
    monkeypatch.setattr(settings, "llm_airgap", True)
    session = AsyncMock()
    mock_router = AsyncMock()
    mock_router.complete_single_model = AsyncMock(
        return_value=('[{"input":"Q?","output":"A"}]', 0.0),
    )
    with patch(
        "app.application.services.dataset_recipe_wizard_service.resolve_dataset_recipe_model_slug",
        new=AsyncMock(return_value="ollama/qwen"),
    ):
        with patch("app.core.llm_router.LiteLLMRouter", return_value=mock_router):
            slug, pairs = await generate_qa_pairs_for_chunks(
                session,
                tenant_id=uuid.uuid4(),
                chunks=["Revenue up 10%"],
            )
    assert slug == "ollama/qwen"
    assert len(pairs) == 1
    mock_router.complete_single_model.assert_awaited_once()


@pytest.mark.asyncio
async def test_compose_snapshot_falls_back_when_resolve_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_llm_enabled", False)
    tenant = Tenant(id=uuid.uuid4(), name="t", slug="t", operator_settings={})
    session = AsyncMock()
    snap = await compose_dataset_recipe_snapshot(session, tenant_id=tenant.id, tenant=tenant)
    assert snap.local_model_slug.startswith("ollama/")


@pytest.mark.asyncio
async def test_resolve_dataset_recipe_local_sovereign(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.dataset_recipe_wizard_service import resolve_dataset_recipe_model_slug

    monkeypatch.setattr(settings, "local_llm_enabled", True)
    monkeypatch.setattr(settings, "llm_airgap", False)
    session = AsyncMock()
    with patch(
        "app.application.services.dataset_recipe_wizard_service.load_routing_config",
        new=AsyncMock(return_value={"routing_mode": "local_sovereign"}),
    ):
        with patch(
            "app.application.services.dataset_recipe_wizard_service.list_tenant_local_adapter_slugs",
            new=AsyncMock(return_value=["ollama/custom"]),
        ):
            slug = await resolve_dataset_recipe_model_slug(session, tenant_id=uuid.uuid4())
    assert slug == "ollama/custom"


@pytest.mark.asyncio
async def test_approve_dataset_recipe_no_pairs_raises() -> None:
    tenant = Tenant(id=uuid.uuid4(), name="t", slug="t", operator_settings={})
    session = AsyncMock()
    with pytest.raises(ValueError, match="No draft pairs"):
        await approve_dataset_recipe_pairs(
            session,
            tenant=tenant,
            payload=DatasetRecipeApproveIn(approved_indices=[0]),
        )


@pytest.mark.asyncio
async def test_approve_all_when_indices_empty() -> None:
    tenant = Tenant(
        id=uuid.uuid4(),
        name="t",
        slug="t",
        operator_settings={
            "dataset_recipe_wizard": {
                "draft_pairs": [
                    {
                        "instruction": "A",
                        "input": "Q1",
                        "output": "O1",
                        "approved": False,
                        "source_chunk": 0,
                    },
                ],
            },
        },
    )
    session = AsyncMock()
    session.commit = AsyncMock()
    snap = await approve_dataset_recipe_pairs(
        session,
        tenant=tenant,
        payload=DatasetRecipeApproveIn(approved_indices=[]),
    )
    assert snap.approved_pair_count == 1


def test_chunk_text_splits_on_paragraph_boundary() -> None:
    segment_a = "A" * 450
    segment_b = "B" * 450
    body = f"{segment_a}\n\n{segment_b}"
    chunks = _chunk_text(body, max_chars=500)
    assert len(chunks) >= 2


def test_parse_csv_bytes_missing_fieldnames() -> None:
    chunks, pairs = parse_csv_bytes(b"")
    assert pairs == []
    assert chunks == []


@pytest.mark.asyncio
async def test_parse_and_store_upload_pdf_preview() -> None:
    tenant = Tenant(id=uuid.uuid4(), name="t", slug="t", operator_settings={})
    session = AsyncMock()
    session.commit = AsyncMock()
    with patch(
        "app.application.services.dataset_recipe_wizard_service.parse_upload_bytes",
        return_value=("pdf", ["chunk one"], []),
    ):
        result = await parse_and_store_upload(
            session,
            tenant=tenant,
            filename="report.pdf",
            content=b"%PDF",
        )
    assert result.source_kind == "pdf"
    assert result.chunk_count == 1
    assert result.preview_text == "chunk one"


def test_compose_snapshot_from_bucket_draft_status() -> None:
    bucket = {
        "draft_pairs": [
            {
                "instruction": "A",
                "input": "Q",
                "output": "O",
                "approved": False,
                "source_chunk": 0,
            },
        ],
    }
    snap = compose_snapshot_from_bucket(bucket=bucket, local_model_slug="ollama/qwen")
    assert snap.status == "draft"


def test_pairs_from_llm_json_skips_non_dict_items() -> None:
    pairs = _pairs_from_llm_json('[{"input":"Q","output":"A"},"skip",{"input":"Q2","output":"A2"}]')
    assert len(pairs) == 2


def test_export_skips_non_dict_rows() -> None:
    tenant = Tenant(
        id=uuid.uuid4(),
        name="t",
        slug="t",
        operator_settings={
            "dataset_recipe_wizard": {
                "draft_pairs": [
                    "bad-row",
                    {
                        "instruction": "A",
                        "input": "Q1",
                        "output": "O1",
                        "approved": True,
                        "source_chunk": 0,
                    },
                ],
            },
        },
    )
    blob, count = export_approved_dataset_recipe_jsonl(tenant)
    assert count == 1
    assert b"Q1" in blob


def test_parse_pdf_bytes_missing_pypdf(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    from app.application.services.dataset_recipe_wizard_service import parse_pdf_bytes

    real_import = builtins.__import__

    def blocked_import(name: str, *args: object, **kwargs: object):  # noqa: ANN401
        if name == "pypdf":
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    with pytest.raises(RuntimeError, match="pypdf"):
        parse_pdf_bytes(b"%PDF-1.4")

    chunks, pairs = parse_csv_bytes(b"plain,text\nno,headers\n")
    assert pairs == []
    assert len(chunks) >= 1


@pytest.mark.asyncio
async def test_resolve_dataset_recipe_local_llm_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.dataset_recipe_wizard_service import resolve_dataset_recipe_model_slug

    monkeypatch.setattr(settings, "local_llm_enabled", False)
    with pytest.raises(RuntimeError, match="Local LLM disabled"):
        await resolve_dataset_recipe_model_slug(AsyncMock(), tenant_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_resolve_dataset_recipe_cloud_allowed_when_local_only_off(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.dataset_recipe_wizard_service import resolve_dataset_recipe_model_slug

    monkeypatch.setattr(settings, "local_llm_enabled", True)
    monkeypatch.setattr(settings, "llm_airgap", False)
    monkeypatch.setattr(settings, "dataset_recipe_local_only", False)
    session = AsyncMock()
    with patch(
        "app.application.services.dataset_recipe_wizard_service.load_routing_config",
        new=AsyncMock(return_value={"routing_mode": "quality"}),
    ):
        with patch(
            "app.application.services.dataset_recipe_wizard_service.list_tenant_local_adapter_slugs",
            new=AsyncMock(return_value=[]),
        ):
            slug = await resolve_dataset_recipe_model_slug(session, tenant_id=uuid.uuid4())
    assert slug.startswith("ollama/")


def test_dataset_recipe_approve_in_dedupes_indices() -> None:
    payload = DatasetRecipeApproveIn(approved_indices=[2, 2, -1, 0])
    assert payload.approved_indices == [0, 2]

    tenant = Tenant(
        id=uuid.uuid4(),
        name="t",
        slug="t",
        operator_settings={
            "dataset_recipe_wizard": {
                "draft_pairs": [
                    {
                        "instruction": "A",
                        "input": "Q1",
                        "output": "O1",
                        "approved": False,
                        "source_chunk": 0,
                    },
                ],
            },
        },
    )
    with pytest.raises(ValueError, match="No approved pairs"):
        export_approved_dataset_recipe_jsonl(tenant)
