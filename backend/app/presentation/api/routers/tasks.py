"""Task backlog ledger (dashboard-admin guarded)."""

from __future__ import annotations

import io
import json
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.presentation.api.deps import DashboardSession, DbSession, dashboard_admin_wall
from app.infrastructure.persistence.models.enums import TaskStatus
from app.infrastructure.persistence.models.task import Task
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable
from app.common.schemas.task import (
    TaskBulkCancelRequest,
    TaskBulkCancelResponse,
    TaskCreateRequest,
    TaskLineageResponse,
    TaskPatchRequest,
    TaskSnapshot,
    TaskWorkspaceFileOut,
    TaskWorkspaceResponse,
)
from app.application.services.mission_kanban import MissionKanbanNotFoundError, fetch_task_lineage
from app.application.services.prompt_injection_guard import (
    PromptInjectionViolationError,
    guard_operator_input,
)
from app.core.logging import get_logger
from app.application.services.task_presenter import attach_agent_labels, build_task_snapshot
from app.application.services.task_ledger import (
    TaskUpsertViolationError,
    apply_task_updates,
    bulk_cancel_task_records,
    cancel_task_record,
    create_task_record,
    fetch_task,
    iter_recent_tasks,
)

_logger = get_logger(__name__)

router = APIRouter(
    tags=["Tasks"],
    dependencies=[Depends(dashboard_admin_wall)],
)


@router.post(
    "",
    response_model=TaskSnapshot,
    status_code=status.HTTP_201_CREATED,
    summary="Queue a swarm execution unit",
)
async def enqueue_task(
    body: TaskCreateRequest,
    db: DbSession,
    _session: DashboardSession,
) -> TaskSnapshot:
    """Create a pending task row anchored to optional swarm/workflow lineage."""

    try:
        entity = await create_task_record(
            db,
            title=body.title,
            task_type_value=body.task_type,
            priority=body.priority,
            payload=dict(body.payload),
            swarm_id=body.swarm_id,
            workflow_id=body.workflow_id,
            parent_task_id=body.parent_task_id,
        )
        await db.commit()
        await db.refresh(entity)
    except TaskUpsertViolationError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected task insert.",
        )
    lbl = await attach_agent_labels(db, [entity])
    return build_task_snapshot(entity, agent_label=lbl.get(entity.agent_id))


@router.get(
    "",
    response_model=list[TaskSnapshot],
    summary="List recent backlog rows",
)
async def list_recent_tasks(
    db: DbSession,
    _session: DashboardSession,
    swarm_id: uuid.UUID | None = Query(default=None, description="Filter by sub-swarm anchor."),
    workflow_id: uuid.UUID | None = Query(default=None),
    agent_id: uuid.UUID | None = Query(default=None, description="Filter rows assigned to a bee."),
    filter_status: TaskStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[TaskSnapshot]:
    """Expose newest backlog rows tuned for dashboards and planner bees."""

    try:
        rows = await iter_recent_tasks(
            db,
            swarm_id=swarm_id,
            workflow_id=workflow_id,
            agent_id=agent_id,
            status=filter_status,
            limit=limit,
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected task listing.",
        )
    labels = await attach_agent_labels(db, rows)
    return [build_task_snapshot(row, agent_label=labels.get(row.agent_id)) for row in rows]


def _task_output_text_and_format(task: Task) -> tuple[str, str]:
    """Best-effort extraction of printable output for downloads."""

    result = task.result
    output_text = ""
    output_format = "text"
    if isinstance(result, dict):
        output_format = str(result.get("format") or "text").lower()
        raw_out = result.get("output") or result.get("content") or result.get("text")
        if isinstance(raw_out, str):
            output_text = raw_out
        elif raw_out is not None:
            output_text = json.dumps(raw_out, indent=2)
        else:
            output_text = json.dumps(result, indent=2)
    elif isinstance(result, str):
        output_text = result
    return output_text, output_format


@router.get(
    "/{task_id}/download",
    summary="Download formatted task output",
)
async def download_task_result(
    task_id: uuid.UUID,
    db: DbSession,
    _session: DashboardSession,
) -> StreamingResponse:
    """Stream CSV/JSON/Markdown/XLSX/text derived from the persisted task result."""

    try:
        row = await fetch_task(db, task_id)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected lookup.",
        )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    output_text, output_format = _task_output_text_and_format(row)
    safe_name = quote(f"task_{task_id}", safe="")
    _logger.info("task_download_ready", task_id=str(task_id), output_format=output_format)

    if output_format == "excel":
        try:
            import openpyxl  # noqa: PLC0415

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Result"
            try:
                data = json.loads(output_text)
                if isinstance(data, list) and data:
                    first = data[0]
                    if isinstance(first, dict):
                        ws.append(list(first.keys()))
                        for item in data:
                            if isinstance(item, dict):
                                ws.append([str(v) for v in item.values()])
                elif isinstance(data, dict):
                    for k, v in data.items():
                        ws.append([str(k), str(v)])
            except json.JSONDecodeError:
                for line in output_text.split("\n"):
                    ws.append(line.split(","))
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            return StreamingResponse(
                buf,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f'attachment; filename="{safe_name}.xlsx"',
                },
            )
        except ImportError:
            output_format = "text"

    if output_format == "csv":
        body = io.BytesIO(output_text.encode("utf-8"))
        return StreamingResponse(
            body,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.csv"'},
        )
    if output_format == "json":
        body = io.BytesIO(output_text.encode("utf-8"))
        return StreamingResponse(
            body,
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.json"'},
        )
    if output_format == "html":
        body = io.BytesIO(output_text.encode("utf-8"))
        return StreamingResponse(
            body,
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.html"'},
        )

    ext = "md" if output_format == "markdown" else "txt"
    body = io.BytesIO(output_text.encode("utf-8"))
    return StreamingResponse(
        body,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.{ext}"'},
    )


@router.get(
    "/{task_id}/lineage",
    response_model=TaskLineageResponse,
    summary="Fetch task parent/children for mission kanban drawer",
)
async def get_task_lineage(
    task_id: uuid.UUID,
    db: DbSession,
    _session: DashboardSession,
) -> TaskLineageResponse:
    """Return parent and child snapshots for hierarchical kanban tasks."""

    try:
        lineage = await fetch_task_lineage(db, task_id)
    except MissionKanbanNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected lineage lookup.",
        )
    return TaskLineageResponse(
        task=lineage.task,
        parent=lineage.parent,
        children=lineage.children,
    )


@router.get(
    "/{task_id}/workspace",
    response_model=TaskWorkspaceResponse,
    summary="List deliverable files linked to a task",
)
async def get_task_workspace(
    task_id: uuid.UUID,
    db: DbSession,
    _session: DashboardSession,
) -> TaskWorkspaceResponse:
    """Return archived deliverables for Hermes-style per-task workspace panel."""

    try:
        row = await fetch_task(db, task_id)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected lookup.",
        )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    stmt = (
        select(TaskFinalDeliverable)
        .where(TaskFinalDeliverable.source_task_id == task_id)
        .order_by(TaskFinalDeliverable.created_at.desc())
        .limit(20)
    )
    try:
        deliverables = list((await db.scalars(stmt)).all())
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected workspace lookup.",
        )

    files = [
        TaskWorkspaceFileOut(
            deliverable_id=item.id,
            title=item.title,
            slug=item.slug,
            archive_relpath=item.archive_relpath,
            preview=(item.markdown_body or "").replace("\n", " ").strip()[:180],
        )
        for item in deliverables
    ]
    return TaskWorkspaceResponse(task_id=task_id, files=files)


@router.get(
    "/{task_id}",
    response_model=TaskSnapshot,
    summary="Fetch backlog detail",
)
async def get_task_snapshot(
    task_id: uuid.UUID,
    db: DbSession,
    _session: DashboardSession,
) -> TaskSnapshot:
    """Return a backlog row with roster metadata for pollinator telemetry."""

    try:
        row = await fetch_task(db, task_id)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected lookup.",
        )

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    labels = await attach_agent_labels(db, [row])
    return build_task_snapshot(row, agent_label=labels.get(row.agent_id))


@router.patch(
    "/{task_id}",
    response_model=TaskSnapshot,
    summary="Patch backlog status or payload excerpts",
)
async def patch_existing_task(
    task_id: uuid.UUID,
    body: TaskPatchRequest,
    db: DbSession,
    _session: DashboardSession,
) -> TaskSnapshot:
    """Update operator-visible fields emitted after LangGraph completions."""

    if (
        body.status is None
        and body.result is None
        and body.error_msg is None
        and body.operator_note is None
        and body.title is None
        and body.task_text is None
        and body.priority is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Provide at least one mutable field.",
        )

    row = await fetch_task(db, task_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    if body.operator_note is not None:
        try:
            guard_operator_input(body.operator_note, field="operator_note")
        except PromptInjectionViolationError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    if body.task_text is not None:
        try:
            guard_operator_input(body.task_text, field="task_text")
        except PromptInjectionViolationError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    if body.title is not None:
        try:
            guard_operator_input(body.title, field="title")
        except PromptInjectionViolationError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    try:
        await apply_task_updates(
            db,
            row,
            status=body.status,
            result=body.result,
            error_msg=body.error_msg,
            operator_note=body.operator_note,
            title=body.title,
            task_text=body.task_text,
            priority=body.priority,
        )
        await db.commit()
        await db.refresh(row)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected task mutation.",
        )
    lbl = await attach_agent_labels(db, [row])
    return build_task_snapshot(row, agent_label=lbl.get(row.agent_id))


@router.post(
    "/bulk-cancel",
    response_model=TaskBulkCancelResponse,
    summary="Bulk remove tasks from mission kanban (cancel)",
)
async def bulk_cancel_existing_tasks(
    body: TaskBulkCancelRequest,
    db: DbSession,
    _session: DashboardSession,
) -> TaskBulkCancelResponse:
    """Cancel multiple backlog rows; running tasks are skipped."""

    try:
        cancelled, skipped_running, not_found = await bulk_cancel_task_records(db, body.task_ids)
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected bulk task removal.",
        )
    return TaskBulkCancelResponse(
        cancelled=cancelled,
        skipped_running=skipped_running,
        not_found=not_found,
    )


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove task from mission kanban (cancel)",
)
async def delete_existing_task(
    task_id: uuid.UUID,
    db: DbSession,
    _session: DashboardSession,
) -> None:
    """Cancel a backlog row so it disappears from operator kanban lists."""

    row = await fetch_task(db, task_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    try:
        await cancel_task_record(db, row)
        await db.commit()
    except TaskUpsertViolationError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected task removal.",
        )


__all__ = ["router"]
