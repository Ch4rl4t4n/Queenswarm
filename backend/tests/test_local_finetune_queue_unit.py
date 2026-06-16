"""Unit tests for Track M LOC9 local fine-tune queue."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.local_finetune_queue_service import (
    FinetuneJobCreateIn,
    approve_and_enqueue_finetune_job,
    build_finetune_training_plan,
    cancel_finetune_job,
    compose_finetune_queue_snapshot,
    count_jsonl_rows,
    create_finetune_job_draft,
    run_finetune_job_simulation,
)
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant
from app.infrastructure.persistence.models.tenant_finetune_job import TenantFinetuneJobORM


def test_finetune_job_create_normalizes_adapter_name() -> None:
    payload = FinetuneJobCreateIn(adapter_name="My Adapter!", base_model="qwen2.5:7b")
    assert payload.adapter_name == "my-adapter"


def test_count_jsonl_skips_invalid_lines(tmp_path) -> None:
    path = tmp_path / "mixed.jsonl"
    path.write_text('{"instruction":"A","input":"Q","output":"O"}\n{bad json\n', encoding="utf-8")
    assert count_jsonl_rows(path) == 1


def test_count_jsonl_rows_rejects_empty(tmp_path) -> None:
    path = tmp_path / "empty.jsonl"
    path.write_text("\n\n", encoding="utf-8")
    with pytest.raises(ValueError, match="No valid JSONL"):
        count_jsonl_rows(path)


def test_count_jsonl_rows(tmp_path) -> None:
    path = tmp_path / "data.jsonl"
    path.write_text(
        '{"instruction":"A","input":"Q","output":"O"}\n{"instruction":"B","input":"Q2","output":"O2"}\n',
        encoding="utf-8",
    )
    assert count_jsonl_rows(path) == 2


@pytest.mark.asyncio
async def test_compose_finetune_queue_snapshot_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_llm_enabled", True)
    monkeypatch.setattr(settings, "local_finetune_queue_enabled", True)
    session = AsyncMock()
    session.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    snap = await compose_finetune_queue_snapshot(session, tenant_id=uuid.uuid4())
    assert snap.enabled is True
    assert snap.gpu_worker_enabled is True


def test_build_finetune_training_plan() -> None:
    plan = build_finetune_training_plan(
        adapter_name="my-adapter",
        base_model="qwen2.5:7b",
        dataset_path="/tmp/data.jsonl",
        epochs=2,
        row_count=10,
    )
    assert plan["ollama_tag"] == "my-adapter"
    assert plan["row_count"] == 10
    assert "unsloth-cli" in plan["command_hint"]


@pytest.mark.asyncio
async def test_compose_finetune_queue_snapshot_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_llm_enabled", False)
    snap = await compose_finetune_queue_snapshot(AsyncMock(), tenant_id=uuid.uuid4())
    assert snap.enabled is False


@pytest.mark.asyncio
async def test_create_finetune_job_draft(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "local_finetune_queue_enabled", True)
    monkeypatch.setattr(settings, "local_finetune_exports_root", str(tmp_path))
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="t", slug="t")
    dataset_dir = tmp_path / f"tenant-{tenant_id}"
    dataset_dir.mkdir(parents=True)
    dataset_file = dataset_dir / "verified-dataset-latest.jsonl"
    dataset_file.write_text(
        json.dumps({"instruction": "A", "input": "Q", "output": "O"}) + "\n",
        encoding="utf-8",
    )

    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock(side_effect=lambda row: row)

    job = await create_finetune_job_draft(
        session,
        tenant=tenant,
        payload=FinetuneJobCreateIn(
            adapter_name="qs-v1",
            base_model="qwen2.5:7b",
            dataset_source="verified_export",
        ),
    )
    assert job.status == "pending_approval"
    assert job.dataset_row_count == 1
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_approve_and_enqueue_finetune_job(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    row = TenantFinetuneJobORM(
        id=job_id,
        tenant_id=tenant_id,
        status="pending_approval",
        adapter_name="qs-v1",
        base_model="qwen2.5:7b",
        dataset_source="verified_export",
        dataset_path="/tmp/x.jsonl",
        dataset_row_count=1,
        epochs=1,
        training_plan_json={},
        metadata_json={},
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=row)
    session.commit = AsyncMock()
    session.refresh = AsyncMock(side_effect=lambda r: r)

    mock_task = MagicMock()
    with patch(
        "app.worker.local_finetune_tasks.run_local_finetune_job_task",
        mock_task,
    ):
        out = await approve_and_enqueue_finetune_job(
            session,
            tenant_id=tenant_id,
            job_id=job_id,
            approved_by_subject="operator@test",
        )
    assert out.status == "queued"
    mock_task.apply_async.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_finetune_job() -> None:
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    row = TenantFinetuneJobORM(
        id=job_id,
        tenant_id=tenant_id,
        status="pending_approval",
        adapter_name="qs-v1",
        base_model="qwen2.5:7b",
        dataset_source="verified_export",
        training_plan_json={},
        metadata_json={},
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=row)
    session.commit = AsyncMock()
    session.refresh = AsyncMock(side_effect=lambda r: r)
    out = await cancel_finetune_job(session, tenant_id=tenant_id, job_id=job_id)
    assert out.status == "cancelled"


@pytest.mark.asyncio
async def test_run_finetune_job_simulation(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "local_finetune_execute_enabled", False)
    dataset = tmp_path / "train.jsonl"
    dataset.write_text(json.dumps({"instruction": "A", "input": "Q", "output": "O"}) + "\n", encoding="utf-8")
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    row = TenantFinetuneJobORM(
        id=job_id,
        tenant_id=tenant_id,
        status="queued",
        adapter_name="qs-v1",
        base_model="qwen2.5:7b",
        dataset_source="upload_path",
        dataset_path=str(dataset),
        dataset_row_count=0,
        epochs=1,
        training_plan_json={},
        metadata_json={},
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=row)
    session.commit = AsyncMock()

    result = await run_finetune_job_simulation(session, job_id=job_id, tenant_id=tenant_id)
    assert result["ok"] is True
    assert row.status == "completed"


@pytest.mark.asyncio
async def test_run_finetune_job_simulation_execute_mode(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "local_finetune_execute_enabled", True)
    script = tmp_path / "run.sh"
    script.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setattr(settings, "local_finetune_host_script", str(script))
    dataset = tmp_path / "train.jsonl"
    dataset.write_text(json.dumps({"instruction": "A", "input": "Q", "output": "O"}) + "\n", encoding="utf-8")
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    row = TenantFinetuneJobORM(
        id=job_id,
        tenant_id=tenant_id,
        status="queued",
        adapter_name="qs-v1",
        base_model="qwen2.5:7b",
        dataset_source="upload_path",
        dataset_path=str(dataset),
        dataset_row_count=0,
        epochs=1,
        training_plan_json={},
        metadata_json={},
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=row)
    session.commit = AsyncMock()
    result = await run_finetune_job_simulation(session, job_id=job_id, tenant_id=tenant_id)
    assert result["ok"] is True
    assert row.status == "completed"


def test_resolve_dataset_upload_path(tmp_path) -> None:
    from app.application.services.local_finetune_queue_service import resolve_dataset_path_for_tenant

    tenant = Tenant(id=uuid.uuid4(), name="t", slug="t")
    dataset = tmp_path / "custom.jsonl"
    dataset.write_text(json.dumps({"instruction": "A", "input": "Q", "output": "O"}) + "\n", encoding="utf-8")
    path, rows = resolve_dataset_path_for_tenant(
        tenant=tenant,
        dataset_source="upload_path",
        dataset_path=str(dataset),
    )
    assert rows == 1
    assert path.endswith("custom.jsonl")


@pytest.mark.asyncio
async def test_finetune_jobs_api_requires_auth() -> None:
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/llm-routing/finetune-jobs")
    assert response.status_code in {401, 403}


def test_count_jsonl_rows_missing_file(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        count_jsonl_rows(tmp_path / "missing.jsonl")


@pytest.mark.asyncio
async def test_approve_finetune_job_not_found() -> None:
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    with pytest.raises(LookupError):
        await approve_and_enqueue_finetune_job(
            session,
            tenant_id=uuid.uuid4(),
            job_id=uuid.uuid4(),
            approved_by_subject="op",
        )


@pytest.mark.asyncio
async def test_cancel_finetune_job_running_rejected() -> None:
    row = TenantFinetuneJobORM(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        status="running",
        adapter_name="x",
        base_model="y",
        dataset_source="verified_export",
        training_plan_json={},
        metadata_json={},
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=row)
    with pytest.raises(ValueError, match="Cannot cancel"):
        await cancel_finetune_job(session, tenant_id=row.tenant_id, job_id=row.id)


@pytest.mark.asyncio
async def test_create_finetune_job_rejects_large_dataset(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "local_finetune_max_dataset_rows", 1)
    monkeypatch.setattr(settings, "local_finetune_exports_root", str(tmp_path))
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="t", slug="t")
    dataset_dir = tmp_path / f"tenant-{tenant_id}"
    dataset_dir.mkdir(parents=True)
    dataset_file = dataset_dir / "verified-dataset-latest.jsonl"
    dataset_file.write_text(
        "\n".join(json.dumps({"instruction": "A", "input": f"Q{i}", "output": "O"}) for i in range(3)) + "\n",
        encoding="utf-8",
    )
    session = AsyncMock()
    with pytest.raises(ValueError, match="exceeds"):
        await create_finetune_job_draft(
            session,
            tenant=tenant,
            payload=FinetuneJobCreateIn(adapter_name="big", base_model="qwen2.5:7b"),
        )


@pytest.mark.asyncio
async def test_run_finetune_job_simulation_failure(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "local_finetune_execute_enabled", False)
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    row = TenantFinetuneJobORM(
        id=job_id,
        tenant_id=tenant_id,
        status="queued",
        adapter_name="qs-v1",
        base_model="qwen2.5:7b",
        dataset_source="upload_path",
        dataset_path=str(tmp_path / "missing.jsonl"),
        dataset_row_count=0,
        epochs=1,
        training_plan_json={},
        metadata_json={},
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=row)
    session.commit = AsyncMock()
    with pytest.raises(FileNotFoundError):
        await run_finetune_job_simulation(session, job_id=job_id, tenant_id=tenant_id)
    assert row.status == "failed"


@pytest.mark.asyncio
async def test_compose_finetune_queue_with_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_llm_enabled", True)
    monkeypatch.setattr(settings, "local_finetune_queue_enabled", True)
    row = TenantFinetuneJobORM(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        status="pending_approval",
        adapter_name="qs-v2",
        base_model="qwen2.5:7b",
        dataset_source="verified_export",
        dataset_path="/tmp/x.jsonl",
        dataset_row_count=5,
        epochs=1,
        training_plan_json={"summary": "plan"},
        metadata_json={},
    )
    session = AsyncMock()
    session.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[row])))
    snap = await compose_finetune_queue_snapshot(session, tenant_id=uuid.uuid4())
    assert len(snap.jobs) == 1
    assert snap.jobs[0].adapter_name == "qs-v2"


def test_resolve_dataset_recipe_path(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.local_finetune_queue_service import resolve_dataset_path_for_tenant

    monkeypatch.setattr(settings, "local_finetune_exports_root", str(tmp_path))
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="t", slug="t")
    dataset_dir = tmp_path / f"tenant-{tenant_id}"
    dataset_dir.mkdir(parents=True)
    dataset_file = dataset_dir / "dataset-recipe-latest.jsonl"
    dataset_file.write_text(json.dumps({"instruction": "A", "input": "Q", "output": "O"}) + "\n", encoding="utf-8")
    path, rows = resolve_dataset_path_for_tenant(
        tenant=tenant,
        dataset_source="dataset_recipe",
        dataset_path=None,
    )
    assert rows == 1
    assert "dataset-recipe" in path


@pytest.mark.asyncio
async def test_approve_finetune_job_invalid_status() -> None:
    row = TenantFinetuneJobORM(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        status="completed",
        adapter_name="x",
        base_model="y",
        dataset_source="verified_export",
        training_plan_json={},
        metadata_json={},
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=row)
    with pytest.raises(ValueError, match="cannot be approved"):
        await approve_and_enqueue_finetune_job(
            session,
            tenant_id=row.tenant_id,
            job_id=row.id,
            approved_by_subject="op",
        )


def test_local_finetune_celery_task_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_finetune_queue_enabled", False)
    from app.worker.local_finetune_tasks import run_local_finetune_job_task

    out = run_local_finetune_job_task(job_id=str(uuid.uuid4()), tenant_id=str(uuid.uuid4()))
    assert out.get("skipped") is True


def test_local_finetune_celery_task_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_finetune_queue_enabled", True)
    with patch(
        "app.application.services.local_finetune_queue_service.run_finetune_job_simulation",
        new=AsyncMock(return_value={"ok": True, "status": "completed"}),
    ):
        from app.worker.local_finetune_tasks import run_local_finetune_job_task

        out = run_local_finetune_job_task(job_id=str(uuid.uuid4()), tenant_id=str(uuid.uuid4()))
    assert out.get("ok") is True


@pytest.mark.asyncio
async def test_run_finetune_execute_missing_script(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "local_finetune_execute_enabled", True)
    monkeypatch.setattr(settings, "local_finetune_host_script", str(tmp_path / "missing.sh"))
    dataset = tmp_path / "train.jsonl"
    dataset.write_text(json.dumps({"instruction": "A", "input": "Q", "output": "O"}) + "\n", encoding="utf-8")
    row = TenantFinetuneJobORM(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        status="queued",
        adapter_name="qs-v1",
        base_model="qwen2.5:7b",
        dataset_source="upload_path",
        dataset_path=str(dataset),
        dataset_row_count=0,
        epochs=1,
        training_plan_json={},
        metadata_json={},
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=row)
    session.commit = AsyncMock()
    with pytest.raises(FileNotFoundError):
        await run_finetune_job_simulation(session, job_id=row.id, tenant_id=row.tenant_id)
    assert row.status == "failed"


@pytest.mark.asyncio
async def test_run_finetune_execute_script_failure(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "local_finetune_execute_enabled", True)
    script = tmp_path / "fail.sh"
    script.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setattr(settings, "local_finetune_host_script", str(script))
    dataset = tmp_path / "train.jsonl"
    dataset.write_text(json.dumps({"instruction": "A", "input": "Q", "output": "O"}) + "\n", encoding="utf-8")
    row = TenantFinetuneJobORM(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        status="queued",
        adapter_name="qs-v1",
        base_model="qwen2.5:7b",
        dataset_source="upload_path",
        dataset_path=str(dataset),
        dataset_row_count=0,
        epochs=1,
        training_plan_json={},
        metadata_json={},
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=row)
    session.commit = AsyncMock()
    with pytest.raises(RuntimeError):
        await run_finetune_job_simulation(session, job_id=row.id, tenant_id=row.tenant_id)
    assert row.status == "failed"


def test_resolve_dataset_missing_file(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.local_finetune_queue_service import resolve_dataset_path_for_tenant

    monkeypatch.setattr(settings, "local_finetune_exports_root", str(tmp_path))
    tenant = Tenant(id=uuid.uuid4(), name="t", slug="t")
    with pytest.raises(FileNotFoundError):
        resolve_dataset_path_for_tenant(
            tenant=tenant,
            dataset_source="verified_export",
            dataset_path=None,
        )


def test_resolve_dataset_upload_path_requires_path() -> None:
    from app.application.services.local_finetune_queue_service import resolve_dataset_path_for_tenant

    tenant = Tenant(id=uuid.uuid4(), name="t", slug="t")
    with pytest.raises(ValueError, match="dataset_path required"):
        resolve_dataset_path_for_tenant(
            tenant=tenant,
            dataset_source="upload_path",
            dataset_path=None,
        )


@pytest.mark.asyncio
async def test_run_finetune_job_not_found() -> None:
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    with pytest.raises(LookupError):
        await run_finetune_job_simulation(session, job_id=uuid.uuid4(), tenant_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_cancel_finetune_job_not_found() -> None:
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    with pytest.raises(LookupError):
        await cancel_finetune_job(session, tenant_id=uuid.uuid4(), job_id=uuid.uuid4())

    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    with pytest.raises(LookupError):
        await cancel_finetune_job(session, tenant_id=uuid.uuid4(), job_id=uuid.uuid4())

