"""Track M LOC9 — GPU fine-tune job queue with operator HITL approve."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.unsloth_bridge_service import (
    litellm_slug_from_ollama_tag,
    normalize_ollama_model_name,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.tenant import Tenant
from app.infrastructure.persistence.models.tenant_finetune_job import TenantFinetuneJobORM

_logger = get_logger(__name__)

FinetuneDatasetSource = Literal["verified_export", "dataset_recipe", "upload_path"]
FinetuneJobStatus = Literal[
    "pending_approval",
    "approved",
    "queued",
    "running",
    "completed",
    "failed",
    "cancelled",
]


class FinetuneJobCreateIn(BaseModel):
    """Create a draft fine-tune job awaiting operator approval."""

    model_config = ConfigDict(extra="forbid")

    adapter_name: str = Field(min_length=2, max_length=64)
    base_model: str = Field(min_length=2, max_length=128)
    dataset_source: FinetuneDatasetSource = "verified_export"
    dataset_path: str | None = Field(default=None, max_length=512)
    epochs: int = Field(default=1, ge=1, le=20)

    @field_validator("adapter_name")
    @classmethod
    def _normalize_adapter(cls, value: str) -> str:
        return normalize_ollama_model_name(value)


class FinetuneJobOut(BaseModel):
    """One fine-tune job row for Settings UI."""

    model_config = ConfigDict(extra="forbid")

    id: str
    status: FinetuneJobStatus
    adapter_name: str
    base_model: str
    dataset_source: FinetuneDatasetSource
    dataset_path: str | None = None
    dataset_row_count: int = 0
    epochs: int = 1
    litellm_slug: str
    celery_task_id: str | None = None
    error_message: str | None = None
    training_plan_summary: str = ""
    created_at: str | None = None
    approved_at: str | None = None


class FinetuneQueueSnapshotOut(BaseModel):
    """Operator snapshot for fine-tune queue panel."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    gpu_worker_enabled: bool
    execute_mode: bool
    jobs: list[FinetuneJobOut] = Field(default_factory=list)
    operator_hint: str = ""


def _serialize(row: TenantFinetuneJobORM) -> FinetuneJobOut:
    plan = row.training_plan_json if isinstance(row.training_plan_json, dict) else {}
    summary = str(plan.get("summary") or plan.get("command_hint") or "")
    return FinetuneJobOut(
        id=str(row.id),
        status=row.status,  # type: ignore[arg-type]
        adapter_name=row.adapter_name,
        base_model=row.base_model,
        dataset_source=row.dataset_source,  # type: ignore[arg-type]
        dataset_path=row.dataset_path,
        dataset_row_count=int(row.dataset_row_count or 0),
        epochs=int(row.epochs or 1),
        litellm_slug=litellm_slug_from_ollama_tag(row.adapter_name),
        celery_task_id=row.celery_task_id,
        error_message=row.error_message,
        training_plan_summary=summary[:400],
        created_at=row.created_at.isoformat() if row.created_at else None,
        approved_at=row.approved_at.isoformat() if row.approved_at else None,
    )


def count_jsonl_rows(path: Path) -> int:
    """Count non-empty JSONL rows in a dataset file."""

    if not path.is_file():
        msg = f"Dataset file not found: {path}"
        raise FileNotFoundError(msg)
    count = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            try:
                json.loads(line)
                count += 1
            except json.JSONDecodeError:
                continue
    if count <= 0:
        msg = f"No valid JSONL rows in dataset: {path}"
        raise ValueError(msg)
    return count


def build_finetune_training_plan(
    *,
    adapter_name: str,
    base_model: str,
    dataset_path: str,
    epochs: int,
    row_count: int,
) -> dict[str, Any]:
    """Build operator-facing Unsloth/QLoRA plan (simulation-first — no GPU in API)."""

    tag = normalize_ollama_model_name(adapter_name)
    slug = litellm_slug_from_ollama_tag(tag)
    command_hint = (
        f"unsloth-cli finetune --base {base_model} --dataset {dataset_path} "
        f"--epochs {epochs} --output ./exports/{tag}.gguf"
    )
    return {
        "summary": f"QLoRA fine-tune {row_count} rows → {tag} ({epochs} epoch(s))",
        "command_hint": command_hint,
        "ollama_tag": tag,
        "litellm_slug": slug,
        "bridge_hint": f"./scripts/operator-unsloth-bridge.sh --gguf ./exports/{tag}.gguf --name {tag} --register",
        "row_count": row_count,
        "simulation_only": not settings.local_finetune_execute_enabled,
    }


def resolve_dataset_path_for_tenant(
    *,
    tenant: Tenant,
    dataset_source: FinetuneDatasetSource,
    dataset_path: str | None,
) -> tuple[str, int]:
    """Resolve dataset path and row count from tenant exports or explicit path."""

    if dataset_source == "upload_path":
        if not dataset_path or not dataset_path.strip():
            msg = "dataset_path required for upload_path source."
            raise ValueError(msg)
        resolved = Path(dataset_path.strip()).expanduser()
        rows = count_jsonl_rows(resolved)
        return str(resolved), rows

    exports_root = Path(settings.local_finetune_exports_root).expanduser()
    if dataset_source == "dataset_recipe":
        candidate = exports_root / f"tenant-{tenant.id}" / "dataset-recipe-latest.jsonl"
    else:
        candidate = exports_root / f"tenant-{tenant.id}" / "verified-dataset-latest.jsonl"

    if dataset_path and dataset_path.strip():
        candidate = Path(dataset_path.strip()).expanduser()

    if not candidate.is_file():
        msg = (
            f"Dataset not found at {candidate}. Export LOC5/LOC6 JSONL first or pass dataset_path."
        )
        raise FileNotFoundError(msg)
    rows = count_jsonl_rows(candidate)
    return str(candidate.resolve()), rows


async def compose_finetune_queue_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> FinetuneQueueSnapshotOut:
    """Return queue snapshot for Settings UI."""

    enabled = settings.local_llm_enabled and settings.local_finetune_queue_enabled
    if not enabled:
        return FinetuneQueueSnapshotOut(
            enabled=False,
            gpu_worker_enabled=False,
            execute_mode=False,
            operator_hint="Enable LOCAL_LLM_ENABLED and local_finetune_queue.",
        )

    rows = list(
        (
            await session.scalars(
                select(TenantFinetuneJobORM)
                .where(TenantFinetuneJobORM.tenant_id == tenant_id)
                .order_by(TenantFinetuneJobORM.created_at.desc())
                .limit(20),
            )
        ).all(),
    )
    return FinetuneQueueSnapshotOut(
        enabled=True,
        gpu_worker_enabled=settings.local_finetune_gpu_worker_enabled,
        execute_mode=settings.local_finetune_execute_enabled,
        jobs=[_serialize(row) for row in rows],
        operator_hint=(
            "Create job → Approve → GPU Celery worker runs plan (simulation by default). "
            "Set LOCAL_FINETUNE_EXECUTE=1 on gpu worker for host Unsloth."
        ),
    )


async def create_finetune_job_draft(
    session: AsyncSession,
    *,
    tenant: Tenant,
    payload: FinetuneJobCreateIn,
) -> FinetuneJobOut:
    """Create pending_approval fine-tune job with validated dataset."""

    path_str, row_count = resolve_dataset_path_for_tenant(
        tenant=tenant,
        dataset_source=payload.dataset_source,
        dataset_path=payload.dataset_path,
    )
    if row_count > settings.local_finetune_max_dataset_rows:
        msg = f"Dataset exceeds {settings.local_finetune_max_dataset_rows} rows."
        raise ValueError(msg)

    plan = build_finetune_training_plan(
        adapter_name=payload.adapter_name,
        base_model=payload.base_model,
        dataset_path=path_str,
        epochs=payload.epochs,
        row_count=row_count,
    )
    row = TenantFinetuneJobORM(
        tenant_id=tenant.id,
        status="pending_approval",
        adapter_name=payload.adapter_name,
        base_model=payload.base_model,
        dataset_source=payload.dataset_source,
        dataset_path=path_str,
        dataset_row_count=row_count,
        epochs=payload.epochs,
        training_plan_json=plan,
        metadata_json={"created_via": "settings_ui"},
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    _logger.info(
        "local_finetune_queue.draft_created",
        tenant_id=str(tenant.id),
        job_id=str(row.id),
        row_count=row_count,
    )
    return _serialize(row)


async def approve_and_enqueue_finetune_job(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    approved_by_subject: str,
) -> FinetuneJobOut:
    """HITL approve and enqueue GPU Celery worker task."""

    row = await session.get(TenantFinetuneJobORM, job_id)
    if row is None or row.tenant_id != tenant_id:
        msg = "Fine-tune job not found."
        raise LookupError(msg)
    if row.status not in {"pending_approval", "approved"}:
        msg = f"Job cannot be approved from status {row.status}."
        raise ValueError(msg)

    row.status = "queued"
    row.approved_at = datetime.now(tz=UTC)
    row.approved_by_subject = approved_by_subject[:256]
    await session.commit()

    from app.worker.local_finetune_tasks import run_local_finetune_job_task

    task_key = str(uuid.uuid4())
    run_local_finetune_job_task.apply_async(
        kwargs={"job_id": str(row.id), "tenant_id": str(tenant_id)},
        task_id=task_key,
        queue="gpu_finetune",
    )
    row.celery_task_id = task_key
    await session.commit()
    await session.refresh(row)
    _logger.info(
        "local_finetune_queue.enqueued",
        tenant_id=str(tenant_id),
        job_id=str(row.id),
        celery_task_id=task_key,
    )
    return _serialize(row)


async def cancel_finetune_job(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
) -> FinetuneJobOut:
    """Cancel a pending or queued job."""

    row = await session.get(TenantFinetuneJobORM, job_id)
    if row is None or row.tenant_id != tenant_id:
        msg = "Fine-tune job not found."
        raise LookupError(msg)
    if row.status in {"running", "completed"}:
        msg = f"Cannot cancel job in status {row.status}."
        raise ValueError(msg)
    row.status = "cancelled"
    await session.commit()
    await session.refresh(row)
    return _serialize(row)


async def run_finetune_job_simulation(
    session: AsyncSession,
    *,
    job_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Execute fine-tune job (simulation or host script when enabled)."""

    row = await session.get(TenantFinetuneJobORM, job_id)
    if row is None or row.tenant_id != tenant_id:
        msg = "Fine-tune job not found."
        raise LookupError(msg)

    row.status = "running"
    await session.commit()

    try:
        path = Path(str(row.dataset_path or ""))
        row_count = count_jsonl_rows(path)
        plan = build_finetune_training_plan(
            adapter_name=row.adapter_name,
            base_model=row.base_model,
            dataset_path=str(path),
            epochs=int(row.epochs),
            row_count=row_count,
        )
        row.training_plan_json = plan
        row.dataset_row_count = row_count

        if settings.local_finetune_execute_enabled:
            import subprocess

            script = Path(settings.local_finetune_host_script).expanduser()
            if not script.is_file():
                msg = f"Host script not found: {script}"
                raise FileNotFoundError(msg)
            proc = subprocess.run(  # noqa: S603
                [
                    str(script),
                    "--dataset",
                    str(path),
                    "--base",
                    row.base_model,
                    "--name",
                    row.adapter_name,
                    "--epochs",
                    str(row.epochs),
                ],
                capture_output=True,
                text=True,
                timeout=int(settings.local_finetune_execute_timeout_sec),
                check=False,
            )
            if proc.returncode != 0:
                msg = (proc.stderr or proc.stdout or "fine-tune script failed")[:2000]
                raise RuntimeError(msg)
            plan["host_stdout"] = (proc.stdout or "")[:4000]
            plan["executed"] = True
        else:
            plan["executed"] = False
            plan["simulation_verified"] = True

        row.status = "completed"
        row.error_message = None
        row.training_plan_json = plan
        meta = dict(row.metadata_json or {})
        meta["completed_at"] = datetime.now(tz=UTC).isoformat()
        row.metadata_json = meta
        await session.commit()
        _logger.info(
            "local_finetune_queue.completed",
            job_id=str(job_id),
            executed=plan.get("executed"),
        )
        return {"ok": True, "status": row.status, "plan": plan}
    except Exception as exc:
        row.status = "failed"
        row.error_message = str(exc)[:2000]
        await session.commit()
        _logger.warning(
            "local_finetune_queue.failed",
            job_id=str(job_id),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise


__all__ = [
    "FinetuneJobCreateIn",
    "FinetuneJobOut",
    "FinetuneQueueSnapshotOut",
    "approve_and_enqueue_finetune_job",
    "build_finetune_training_plan",
    "cancel_finetune_job",
    "compose_finetune_queue_snapshot",
    "count_jsonl_rows",
    "create_finetune_job_draft",
    "resolve_dataset_path_for_tenant",
    "run_finetune_job_simulation",
]
