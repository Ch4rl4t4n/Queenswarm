"""Bootstrap HiveMind learning — tagged [INSIGHT] docs via Auto-Graphify + optional routine trigger."""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.application.services.auto_graphify_service import AutoGraphifyService, graphify_upload_dir
from app.application.services.hivemind_ingest_overview import build_hivemind_ingest_overview
from app.application.services.supervisor.routine_service import trigger_supervisor_routine_now
from app.core.database import async_session
from app.infrastructure.persistence.models.graphify_batch import GraphifyBatchORM, GraphifyStatusORM
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine
from sqlalchemy import select

DEFAULT_TENANT_ID = uuid.UUID("e098b808-8974-4bae-a6e1-de10bf6a2880")
SENTINEL_ROUTINE_ID = uuid.UUID("f6d6d409-ae52-46b5-bf29-c263aaac0d41")

_INSIGHTS: list[tuple[str, str]] = [
    (
        "hivemind/2026-05-22-quality-contract-bootstrap.md",
        """# [INSIGHT] HiveMind Quality Contract bootstrap

#hivemind-candidate #ai-agents #queenswarm #2026-05-22

## Source
- url: queenswarm.love/knowledge/hivemind-ingest
- captured_by: operator bootstrap
- captured_at: {ts}

## Key findings
- VaultDocuments must carry the `hivemind-candidate` tag for Auto-Graphify compliance metrics.
- Supervisor durable/inprocess sub-agents currently run harness stubs; real [INSIGHT] pages come from Notion `mcp_invoke` or Auto-Graphify folder upload until LLM execution is wired.
- Solo operator should prefer **Knowledge → Auto-Graphify** upload or approve SCV proposals for codebase lane.

## Confidence
high — verified against production runtime and ingest dashboard code paths.
""",
    ),
    (
        "hivemind/2026-05-22-sentinel-read-only-loop.md",
        """# [INSIGHT] Sentinel read-only intelligence loop

#hivemind-candidate #sentinel #research #2026-05-22

## Source
- url: internal://routine/sentinel-daily-scan
- captured_by: Sentinel bootstrap
- captured_at: {ts}

## Key findings
- Sentinel colony is read-only: scan world signals, trends, and mini-app opportunities without external API spend.
- Each verified signal should become one Notion [INSIGHT] page tagged `hivemind-candidate` for graph ingest.
- Routine **Sentinel daily scan** (06:00 UTC cron) is the scheduled entry point; manual trigger available from `/agents` routines.

## Confidence
medium — workflow matches Virtual Company template; LLM+Notion write path pending full sub-agent execution wiring.
""",
    ),
    (
        "hivemind/2026-05-22-solo-operator-playbook.md",
        """# [INSIGHT] Solo operator HiveMind playbook

#hivemind-candidate #operations #2026-05-22

## Source
- url: queenswarm.love/agents
- captured_by: Queen orchestrator seed
- captured_at: {ts}

## Key findings
- **Code changes**: Execution Studio → Pending SCV proposals → Queen Maintainer PR-only on `queen-maintainer/*`.
- **Knowledge growth**: Auto-Graphify markdown upload or Sentinel/Forager ingest with topic tags.
- **Do not confuse** session Approve on `/agents` (supervisor guardrails) with SCV proposal approval in Execution Studio.

## Confidence
high — aligns with solo deployment docs and operator P0 backlog.
""",
    ),
]


async def _run_graphify(*, tenant_id: uuid.UUID) -> uuid.UUID:
    ts = datetime.now(tz=UTC).isoformat()
    async with async_session() as db:
        batch = GraphifyBatchORM(
            tenant_id=tenant_id,
            created_by_subject="bootstrap:hivemind_learning",
            status=GraphifyStatusORM.QUEUED,
            folder_label="hivemind-learning-bootstrap",
            file_count=len(_INSIGHTS),
            storage_meta={"filenames": [name for name, _ in _INSIGHTS]},
        )
        db.add(batch)
        await db.flush()

        upload_dir = graphify_upload_dir(tenant_id=tenant_id, batch_id=batch.id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        for rel_path, body in _INSIGHTS:
            dest = upload_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(body.format(ts=ts), encoding="utf-8")

        service = AutoGraphifyService(db=db)
        completed = await service.process_batch(tenant_id=tenant_id, batch_id=batch.id)
        await db.commit()
        print(
            f"graphify batch={completed.id} ingested={completed.items_ingested} "
            f"graph_nodes={completed.graph_nodes_created} vectors={completed.vectors_embedded} "
            f"pollen={completed.pollen_earned}"
        )
        return completed.id


async def _trigger_sentinel(*, tenant_id: uuid.UUID) -> uuid.UUID | None:
    async with async_session() as db:
        routine = await db.scalar(
            select(SupervisorRoutine).where(
                SupervisorRoutine.id == SENTINEL_ROUTINE_ID,
                SupervisorRoutine.tenant_id == tenant_id,
            ),
        )
        if routine is None:
            routine = await db.scalar(
                select(SupervisorRoutine).where(SupervisorRoutine.name == "Sentinel daily scan").limit(1),
            )
        if routine is None:
            print("sentinel_routine_not_found")
            return None
        if not list(routine.roles or []):
            routine.roles = ["researcher"]
        session_id = await trigger_supervisor_routine_now(db, routine=routine)
        await db.commit()
        print(f"sentinel_session={session_id}")
        return session_id


async def _print_compliance(*, tenant_id: uuid.UUID) -> None:
    async with async_session() as db:
        overview = await build_hivemind_ingest_overview(db, tenant_id=tenant_id, window_hours=24)
        headline = overview.get("headline") or {}
        print(
            f"compliance={headline.get('contract_compliance_pct')}% "
            f"tagged={headline.get('hivemind_candidate_pages')}/"
            f"{headline.get('vault_documents_last_window')}"
        )
        for note in overview.get("notes") or []:
            print(f"note: {note}")


async def main(tenant_id: uuid.UUID) -> int:
    await _run_graphify(tenant_id=tenant_id)
    await _trigger_sentinel(tenant_id=tenant_id)
    await _print_compliance(tenant_id=tenant_id)
    return 0


if __name__ == "__main__":
    tid = uuid.UUID(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TENANT_ID
    raise SystemExit(asyncio.run(main(tid)))
