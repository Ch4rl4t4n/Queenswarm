"""Dump & Sleep — overnight folder/voice ingest with verified morning briefing."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.dreamer_service import DreamerService
from app.application.services.hive_tier import FIXED_ORCHESTRATOR_AGENT_NAME
from app.application.services.verified_pollen_leaderboard import record_verified_pollen_reward
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.dump_sleep_batch import DumpSleepBatchORM, DumpSleepStatusORM
from app.infrastructure.persistence.models.knowledge import KnowledgeItem, LearningLog
from app.infrastructure.persistence.models.reward import PollenReward

logger = get_logger(__name__)

_STALLED_RE = re.compile(r"\b(stalled|blocked|waiting|on hold|stuck)\b", re.IGNORECASE)
_TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".json", ".csv", ".py", ".html", ".xml", ".yaml", ".yml", ".log"}


def dump_sleep_upload_dir(*, tenant_id: uuid.UUID, batch_id: uuid.UUID) -> Path:
    """Return tenant-scoped upload directory for one batch."""

    root = Path(settings.dump_sleep_upload_root).expanduser().resolve()
    return root / str(tenant_id) / str(batch_id)


def _read_text_file(path: Path) -> str | None:
    """Read UTF-8 text from supported dump files."""

    suffix = path.suffix.lower()
    if suffix not in _TEXT_SUFFIXES:
        return None
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    text = raw.strip()
    return text if text else None


def _count_stalled_signals(*, texts: list[str]) -> int:
    """Heuristic count of stalled-project language in ingested corpus."""

    total = 0
    for block in texts:
        total += len(_STALLED_RE.findall(block))
    return total


def _build_briefing_md(
    *,
    items_ingested: int,
    file_count: int,
    stalled_signals: int,
    pollen_earned: float,
    dream_digest: str,
    voice_note: str | None,
) -> str:
    """Compose verified morning briefing markdown."""

    lines = [
        "# Overnight Swarm Report",
        "",
        f"- Files received: **{file_count}**",
        f"- Memory items ingested: **{items_ingested}**",
        f"- Stalled signals detected: **{stalled_signals}**",
        f"- Pollen earned: **{pollen_earned:.1f}**",
        "",
        "## Morning priorities",
    ]
    if voice_note and voice_note.strip():
        lines.append(f"- Voice note captured: _{voice_note.strip()[:240]}_")
    if items_ingested == 0:
        lines.append("- No readable text files found — add `.txt` or `.md` dumps.")
    else:
        lines.append("- Review consolidated insights in Knowledge hub.")
        if stalled_signals > 0:
            lines.append("- Triage stalled projects flagged overnight.")
        lines.append("- Approve verified tasks before they reach users.")
    if dream_digest.strip():
        lines.extend(["", "## Dream digest", dream_digest.strip()[:4000]])
    return "\n".join(lines).strip() + "\n"


async def _resolve_orchestrator_agent(session: AsyncSession, *, tenant_id: uuid.UUID) -> Agent | None:
    """Find tenant orchestrator bee for pollen credit."""

    rows = list(
        (
            await session.scalars(
                select(Agent).where(Agent.tenant_id == tenant_id).order_by(Agent.created_at.asc()).limit(40),
            )
        ).all(),
    )
    for row in rows:
        if row.name.strip().lower() == FIXED_ORCHESTRATOR_AGENT_NAME.lower():
            return row
    return rows[0] if rows else None


async def _grant_dump_sleep_pollen(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    amount: float,
    batch_id: uuid.UUID,
) -> float:
    """Credit verified pollen to orchestrator after overnight ingest."""

    if amount <= 0.0:
        return 0.0
    agent = await _resolve_orchestrator_agent(session, tenant_id=tenant_id)
    if agent is None:
        logger.warning("dump_sleep.pollen_skipped_no_agent", tenant_id=str(tenant_id), batch_id=str(batch_id))
        return 0.0
    stamp = datetime.now(tz=UTC)
    session.add(
        PollenReward(
            agent_id=agent.id,
            task_id=None,
            amount=float(amount),
            reason="Verified Dump & Sleep overnight ingest.",
            verified_reward=True,
        ),
    )
    agent.pollen_points = float(agent.pollen_points) + float(amount)
    session.add(
        LearningLog(
            agent_id=agent.id,
            task_id=None,
            insight_text=f"Dump & Sleep batch {batch_id} consolidated overnight.",
            applied_at=stamp,
            pollen_earned=float(amount),
            tenant_id=tenant_id,
        ),
    )
    await session.flush()
    if agent.swarm_id is not None:
        await record_verified_pollen_reward(
            agent_id=agent.id,
            swarm_id=agent.swarm_id,
            amount=float(amount),
            task_id=None,
        )
    return float(amount)


class DumpSleepService:
    """Queue and process overnight folder dumps."""

    def __init__(self, *, db: AsyncSession) -> None:
        self._db = db

    async def get_batch(self, *, tenant_id: uuid.UUID, batch_id: uuid.UUID) -> DumpSleepBatchORM | None:
        """Load one tenant-scoped batch."""

        return await self._db.scalar(
            select(DumpSleepBatchORM).where(
                DumpSleepBatchORM.id == batch_id,
                DumpSleepBatchORM.tenant_id == tenant_id,
            ),
        )

    async def latest_overnight_report(
        self,
        *,
        tenant_id: uuid.UUID,
        window_hours: int = 24,
    ) -> DumpSleepBatchORM | None:
        """Return newest completed batch inside the reporting window."""

        since = datetime.now(tz=UTC) - timedelta(hours=max(1, window_hours))
        return await self._db.scalar(
            select(DumpSleepBatchORM)
            .where(
                DumpSleepBatchORM.tenant_id == tenant_id,
                DumpSleepBatchORM.status == DumpSleepStatusORM.COMPLETED,
                DumpSleepBatchORM.created_at >= since,
            )
            .order_by(DumpSleepBatchORM.created_at.desc())
            .limit(1),
        )

    async def process_batch(
        self,
        *,
        tenant_id: uuid.UUID,
        batch_id: uuid.UUID,
        dreamer: DreamerService | None = None,
    ) -> DumpSleepBatchORM:
        """Ingest files, run dreaming, award pollen, and publish briefing."""

        batch = await self.get_batch(tenant_id=tenant_id, batch_id=batch_id)
        if batch is None:
            raise ValueError(f"Dump batch not found: {batch_id}")
        batch.status = DumpSleepStatusORM.PROCESSING
        batch.error_text = None
        await self._db.flush()

        log = logger.bind(agent_id="dump_sleep", swarm_id=str(tenant_id), task_id=str(batch_id))
        upload_dir = dump_sleep_upload_dir(tenant_id=tenant_id, batch_id=batch_id)
        ingested_texts: list[str] = []

        try:
            if batch.voice_note_text and batch.voice_note_text.strip():
                ingested_texts.append(batch.voice_note_text.strip())

            if upload_dir.is_dir():
                for path in sorted(upload_dir.iterdir()):
                    if not path.is_file():
                        continue
                    if path.stat().st_size > settings.dump_sleep_max_file_bytes:
                        log.warning("dump_sleep.file_skipped_size", filename=path.name)
                        continue
                    text = _read_text_file(path)
                    if not text:
                        continue
                    ingested_texts.append(text)
                    self._db.add(
                        KnowledgeItem(
                            tenant_id=tenant_id,
                            source_url=f"dump-sleep://{batch_id}/{path.name}",
                            source_type="dump_sleep",
                            content_text=text[: settings.dump_sleep_max_content_chars],
                            confidence_score=0.72,
                            topic_tags=["dump_sleep", "overnight", f"batch:{batch_id}"],
                            decay_factor=1.0,
                            scraped_at=datetime.now(tz=UTC),
                        ),
                    )

            await self._db.flush()
            batch.items_ingested = len(ingested_texts)
            batch.stalled_signals = _count_stalled_signals(texts=ingested_texts)

            dream_digest = ""
            dream_cycle_id: uuid.UUID | None = None
            if dreamer is not None and ingested_texts:
                try:
                    cycle = await dreamer.run_cycle(tenant_id=tenant_id, window_hours=settings.dreaming_window_hours)
                    dream_digest = cycle.digest_md or ""
                    dream_cycle_id = cycle.id
                except Exception as dream_exc:  # noqa: BLE001
                    log.warning("dump_sleep.dreaming_failed", error=str(dream_exc))
                    dream_digest = f"_Dreaming cycle skipped: {dream_exc}_"

            pollen = float(batch.items_ingested) * float(settings.dump_sleep_pollen_per_item)
            batch.pollen_earned = await _grant_dump_sleep_pollen(
                self._db,
                tenant_id=tenant_id,
                amount=pollen,
                batch_id=batch_id,
            )
            batch.dream_cycle_id = dream_cycle_id
            batch.briefing_md = _build_briefing_md(
                items_ingested=batch.items_ingested,
                file_count=batch.file_count,
                stalled_signals=batch.stalled_signals,
                pollen_earned=batch.pollen_earned,
                dream_digest=dream_digest,
                voice_note=batch.voice_note_text,
            )
            batch.status = DumpSleepStatusORM.COMPLETED
            batch.processed_at = datetime.now(tz=UTC)
            await self._db.flush()
            log.info(
                "dump_sleep.completed",
                items_ingested=batch.items_ingested,
                pollen_earned=batch.pollen_earned,
            )
            return batch
        except Exception as exc:  # noqa: BLE001
            batch.status = DumpSleepStatusORM.FAILED
            batch.error_text = str(exc)[:2000]
            batch.processed_at = datetime.now(tz=UTC)
            await self._db.flush()
            log.exception("dump_sleep.failed", error=str(exc))
            raise


__all__ = [
    "DumpSleepService",
    "dump_sleep_upload_dir",
]
