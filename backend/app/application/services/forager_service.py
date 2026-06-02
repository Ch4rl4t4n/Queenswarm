"""Tenant-scoped service for dynamic Forager management and integrations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.agent_catalog import create_agent_record
from app.application.services.supervisor.routine_service import create_supervisor_routine, trigger_supervisor_routine_now
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.agent_config import AgentConfig
from app.infrastructure.persistence.models.agent_template import AgentTemplateORM
from app.infrastructure.persistence.models.enums import AgentRole, AgentStatus
from app.infrastructure.persistence.models.forager import ForagerORM
from app.infrastructure.persistence.models.knowledge import KnowledgeItem
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine

_SOCIAL_INTEL_SOURCE_TYPES = frozenset({"youtube", "twitter", "x"})


def _social_intel_routine_goal(forager: ForagerORM) -> str:
    """Goal template for YouTube/X foragers with mandatory Grok verification."""

    return (
        f"Social intel forager '{forager.name}' ({forager.source_type}): "
        "For each Knowledge item tagged pending-grok-verification from this forager: "
        "(1) summarize in 3 bullets, (2) run Grok truth arbiter (xai/grok-3-mini) on EVERY factual "
        "claim — drop verdict=false, (3) score tech/business fit, (4) write HiveMind insight ONLY "
        "when Grok confirms true+high/medium or partial+medium — tag hivemind-candidate, social-intel. "
        "Use skill social-intel-evaluator."
    )


def _routine_skills_for_forager(forager: ForagerORM) -> list[str]:
    """Skills injected into supervisor routine for one forager."""

    if forager.source_type in _SOCIAL_INTEL_SOURCE_TYPES:
        return ["hivemind", "retrieval", "social-intel-evaluator"]
    return ["hivemind", "retrieval"]


class ForagerService:
    """CRUD + orchestration helper for foragers within one tenant."""

    def __init__(self, *, db: AsyncSession) -> None:
        """Initialize service with request-scoped async DB session."""

        self._db = db

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[ForagerORM]:
        """List all foragers for one tenant."""

        rows = await self._db.scalars(
            select(ForagerORM)
            .where(ForagerORM.tenant_id == tenant_id)
            .order_by(ForagerORM.updated_at.desc(), ForagerORM.name.asc()),
        )
        return list(rows)

    async def get_by_id(self, tenant_id: uuid.UUID, forager_id: uuid.UUID) -> ForagerORM | None:
        """Fetch one forager by id in tenant scope."""

        return await self._db.scalar(
            select(ForagerORM).where(
                ForagerORM.id == forager_id,
                ForagerORM.tenant_id == tenant_id,
            ),
        )

    async def create(
        self,
        *,
        tenant_id: uuid.UUID,
        name: str,
        description: str,
        source_type: str,
        source_config: dict[str, Any],
        filter_config: dict[str, Any],
        prompt_template: str,
        tools: list[str],
        is_active: bool,
        agent_template_id: uuid.UUID | None,
        schedule: dict[str, Any] | None,
        created_by_subject: str | None,
    ) -> ForagerORM:
        """Create one forager row and optionally bind a supervisor routine."""

        row = ForagerORM(
            tenant_id=tenant_id,
            name=name.strip(),
            description=description.strip(),
            source_type=source_type.strip().lower() or "rss",
            source_config=dict(source_config or {}),
            filter_config=dict(filter_config or {}),
            prompt_template=prompt_template.strip(),
            tools=[item.strip() for item in tools if item.strip()],
            is_active=bool(is_active),
            agent_template_id=agent_template_id,
        )
        self._db.add(row)
        await self._db.flush()
        await self._upsert_routine_link(
            forager=row,
            schedule=schedule,
            created_by_subject=created_by_subject,
            tenant_id=tenant_id,
        )
        await self._db.flush()
        return row

    async def update(
        self,
        *,
        tenant_id: uuid.UUID,
        forager_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        source_type: str | None = None,
        source_config: dict[str, Any] | None = None,
        filter_config: dict[str, Any] | None = None,
        prompt_template: str | None = None,
        tools: list[str] | None = None,
        is_active: bool | None = None,
        agent_template_id: uuid.UUID | None = None,
        schedule: dict[str, Any] | None = None,
        created_by_subject: str | None = None,
    ) -> ForagerORM | None:
        """Update one forager and optionally refresh routine linkage."""

        row = await self.get_by_id(tenant_id, forager_id)
        if row is None:
            return None
        if name is not None:
            row.name = name.strip()
        if description is not None:
            row.description = description.strip()
        if source_type is not None:
            row.source_type = source_type.strip().lower() or "rss"
        if source_config is not None:
            row.source_config = dict(source_config)
        if filter_config is not None:
            row.filter_config = dict(filter_config)
        if prompt_template is not None:
            row.prompt_template = prompt_template.strip()
        if tools is not None:
            row.tools = [item.strip() for item in tools if item.strip()]
        if is_active is not None:
            row.is_active = bool(is_active)
        if agent_template_id is not None:
            row.agent_template_id = agent_template_id
        if schedule is not None:
            await self._upsert_routine_link(
                forager=row,
                schedule=schedule,
                created_by_subject=created_by_subject,
                tenant_id=tenant_id,
            )
        await self._db.flush()
        return row

    async def delete(self, tenant_id: uuid.UUID, forager_id: uuid.UUID) -> bool:
        """Delete one forager and deactivate linked routine when present."""

        row = await self.get_by_id(tenant_id, forager_id)
        if row is None:
            return False
        if row.supervisor_routine_id is not None:
            routine = await self._db.get(SupervisorRoutine, row.supervisor_routine_id)
            if routine is not None:
                routine.is_active = False
                routine.status = "disabled"
        result = await self._db.execute(
            delete(ForagerORM).where(
                ForagerORM.id == forager_id,
                ForagerORM.tenant_id == tenant_id,
            ),
        )
        await self._db.flush()
        return bool(result.rowcount and result.rowcount > 0)

    async def toggle_enabled(self, *, tenant_id: uuid.UUID, forager_id: uuid.UUID, enabled: bool) -> ForagerORM | None:
        """Enable/disable one forager within tenant scope."""

        row = await self.get_by_id(tenant_id, forager_id)
        if row is None:
            return None
        row.is_active = bool(enabled)
        if row.supervisor_routine_id is not None:
            routine = await self._db.get(SupervisorRoutine, row.supervisor_routine_id)
            if routine is not None:
                routine.is_active = bool(enabled)
                routine.status = "scheduled" if enabled else "disabled"
        await self._db.flush()
        return row

    async def ingest_records(
        self,
        *,
        tenant_id: uuid.UUID,
        forager_id: uuid.UUID,
        records: list[dict[str, Any]],
    ) -> int:
        """Persist forager-produced records into tenant knowledge store."""

        row = await self.get_by_id(tenant_id, forager_id)
        if row is None:
            return 0
        default_tags = [str(tag).strip() for tag in list((row.filter_config or {}).get("default_tags") or []) if str(tag).strip()]
        inserted = 0
        for record in records:
            content_text = str(record.get("content_text") or "").strip()
            if not content_text:
                continue
            source_url = str(record.get("source_url") or "").strip() or None
            item_tags = [str(tag).strip() for tag in list(record.get("topic_tags") or []) if str(tag).strip()]
            merged_tags = list(dict.fromkeys([*default_tags, f"forager:{row.id}", *item_tags]))[:32]
            confidence = float(record.get("confidence_score") or 0.65)
            knowledge = KnowledgeItem(
                tenant_id=tenant_id,
                source_url=source_url,
                source_type=f"forager:{row.source_type}",
                content_text=content_text,
                confidence_score=max(0.0, min(1.0, confidence)),
                topic_tags=merged_tags,
                decay_factor=1.0,
                scraped_at=datetime.now(tz=UTC),
            )
            self._db.add(knowledge)
            inserted += 1
        await self._db.flush()
        return inserted

    async def spawn_agent_from_forager(
        self,
        *,
        tenant_id: uuid.UUID,
        forager_id: uuid.UUID,
        swarm_id: uuid.UUID | None = None,
    ) -> tuple[Agent, AgentConfig] | None:
        """Spawn one worker bee preconfigured from forager + template metadata."""

        row = await self.get_by_id(tenant_id, forager_id)
        if row is None:
            return None
        template: AgentTemplateORM | None = None
        if row.agent_template_id is not None:
            template = await self._db.scalar(
                select(AgentTemplateORM).where(
                    AgentTemplateORM.id == row.agent_template_id,
                    AgentTemplateORM.tenant_id == tenant_id,
                ),
            )
        tools = list(row.tools or [])
        if template is not None and template.tools:
            tools = list(dict.fromkeys([*template.tools, *tools]))
        system_prompt = row.prompt_template.strip() or (template.prompt_template.strip() if template is not None else "")
        if not system_prompt:
            system_prompt = "You are a specialized forager agent ingesting signals into HiveMind."
        agent = await create_agent_record(
            self._db,
            name=f"{row.name.strip()} Forager",
            role=AgentRole.LEARNER,
            status=AgentStatus.IDLE,
            swarm_id=swarm_id,
            config={
                "origin": "forager_spawn",
                "forager_id": str(row.id),
                "source_type": row.source_type,
                "hive_tier": "worker",
            },
        )
        cfg = AgentConfig(
            agent_id=agent.id,
            system_prompt=system_prompt,
            user_prompt_template=None,
            tools=tools,
            output_format="markdown",
            output_destination="knowledge",
            output_config={
                "forager_id": str(row.id),
                "forager_source_type": row.source_type,
                "spawned_from_template": str(template.id) if template is not None else "forager_direct",
                "spawned_template_category": template.category if template is not None else "forager",
                "source_config": dict(row.source_config or {}),
            },
            schedule_type="on_demand",
            schedule_value=None,
            is_active=True,
        )
        self._db.add(cfg)
        await self._db.flush()
        return agent, cfg

    async def trigger_manual_run(
        self,
        *,
        tenant_id: uuid.UUID,
        forager_id: uuid.UUID,
        records: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        """Run one manual forager cycle: ingest into HiveMind + optionally trigger routine."""

        row = await self.get_by_id(tenant_id, forager_id)
        if row is None:
            return None
        if not row.is_active:
            return {
                "forager_id": str(row.id),
                "ingested": 0,
                "scraped": 0,
                "routine_triggered": False,
                "routine_session_id": None,
                "status": "inactive",
            }

        payload_records = list(records or [])
        scraped_count = 0
        if not payload_records and row.source_type in {"youtube", "twitter", "x"}:
            from app.application.services.social_intel_runner import scrape_forager_sources

            scraped = await scrape_forager_sources(self._db, forager=row)
            scraped_count = len(scraped)
            default_tags = [
                str(tag).strip()
                for tag in list((row.filter_config or {}).get("default_tags") or [])
                if str(tag).strip()
            ]
            from app.application.services.social_intel_scraper import scraped_item_to_ingest_record

            payload_records = [
                scraped_item_to_ingest_record(item, default_tags=default_tags) for item in scraped
            ]

        if not payload_records:
            fallback_content = str((row.source_config or {}).get("seed_content") or "").strip()
            if fallback_content:
                payload_records = [
                    {
                        "source_url": str((row.source_config or {}).get("seed_url") or "").strip() or None,
                        "content_text": fallback_content,
                        "confidence_score": float((row.source_config or {}).get("seed_confidence") or 0.65),
                        "topic_tags": list((row.filter_config or {}).get("default_tags") or []),
                    },
                ]

        ingested = 0
        if payload_records:
            ingested = await self.ingest_records(
                tenant_id=tenant_id,
                forager_id=row.id,
                records=payload_records,
            )

        triggered = False
        routine_session_id: str | None = None
        if row.supervisor_routine_id is not None:
            routine = await self._db.get(SupervisorRoutine, row.supervisor_routine_id)
            if routine is not None and bool(routine.is_active):
                session_id = await trigger_supervisor_routine_now(self._db, routine=routine)
                triggered = True
                routine_session_id = str(session_id)

        return {
            "forager_id": str(row.id),
            "ingested": int(ingested),
            "scraped": scraped_count,
            "routine_triggered": triggered,
            "routine_session_id": routine_session_id,
            "status": "triggered",
        }

    async def _upsert_routine_link(
        self,
        *,
        forager: ForagerORM,
        schedule: dict[str, Any] | None,
        created_by_subject: str | None,
        tenant_id: uuid.UUID,
    ) -> None:
        """Create/update/deactivate supervisor routine bound to a forager."""

        spec = dict(schedule or {})
        enabled = bool(spec.get("enabled"))
        if not enabled:
            if forager.supervisor_routine_id is not None:
                routine = await self._db.get(SupervisorRoutine, forager.supervisor_routine_id)
                if routine is not None:
                    routine.is_active = False
                    routine.status = "disabled"
            forager.supervisor_routine_id = None
            return

        schedule_kind = str(spec.get("schedule_kind") or "interval")
        interval_seconds = spec.get("interval_seconds")
        cron_expr = spec.get("cron_expr")
        runtime_mode = str(spec.get("runtime_mode") or "durable")
        context_payload = {
            "forager_id": str(forager.id),
            "forager_name": forager.name,
            "forager_source_type": forager.source_type,
            "forager_auto_ingest": True,
            "source_config": dict(forager.source_config or {}),
            "filters": dict(forager.filter_config or {}),
        }
        if forager.supervisor_routine_id is None:
            goal = (
                _social_intel_routine_goal(forager)
                if forager.source_type in _SOCIAL_INTEL_SOURCE_TYPES
                else f"Run forager '{forager.name}' source='{forager.source_type}' and update HiveMind."
            )
            routine = await create_supervisor_routine(
                self._db,
                name=f"Forager · {forager.name}",
                goal_template=goal,
                created_by_subject=created_by_subject,
                schedule_kind=schedule_kind if schedule_kind in {"interval", "cron", "event"} else "interval",
                interval_seconds=int(interval_seconds) if isinstance(interval_seconds, int) else None,
                cron_expr=str(cron_expr).strip() if cron_expr else None,
                runtime_mode=runtime_mode if runtime_mode in {"inprocess", "durable"} else "durable",
                roles=["researcher", "critic"],
                retrieval_contract="forager-ingest",
                skills=_routine_skills_for_forager(forager),
                context_payload=context_payload,
                tenant_id=tenant_id,
            )
            forager.supervisor_routine_id = routine.id
            return

        routine = await self._db.get(SupervisorRoutine, forager.supervisor_routine_id)
        if routine is None:
            forager.supervisor_routine_id = None
            await self._upsert_routine_link(
                forager=forager,
                schedule=spec,
                created_by_subject=created_by_subject,
                tenant_id=tenant_id,
            )
            return
        routine.name = f"Forager · {forager.name}"
        routine.goal_template = (
            _social_intel_routine_goal(forager)
            if forager.source_type in _SOCIAL_INTEL_SOURCE_TYPES
            else f"Run forager '{forager.name}' source='{forager.source_type}' and update HiveMind."
        )
        routine.skills = _routine_skills_for_forager(forager)
        routine.schedule_kind = schedule_kind if schedule_kind in {"interval", "cron", "event"} else "interval"
        routine.interval_seconds = int(interval_seconds) if isinstance(interval_seconds, int) else routine.interval_seconds
        routine.cron_expr = str(cron_expr).strip() if cron_expr else None
        routine.runtime_mode = runtime_mode if runtime_mode in {"inprocess", "durable"} else "durable"
        routine.context_payload = context_payload
        routine.is_active = True
        routine.status = "scheduled"


__all__ = ["ForagerService"]
