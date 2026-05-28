"""Server-side Virtual Company swarm wizard — mirrors frontend Swarm Builder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.agent_catalog import AgentCatalogError, create_agent_record
from app.application.services.sub_swarm_catalog import create_sub_swarm
from app.application.services.supervisor.routine_service import create_supervisor_routine
from app.application.services.virtual_company_profile import (
    DEPARTMENT_CONNECTOR_MAP,
    profile_context_block,
    profile_from_tenant,
)
from app.infrastructure.persistence.models.agent_config import AgentConfig
from app.infrastructure.persistence.models.enums import AgentRole, AgentStatus, SwarmPurpose
from app.infrastructure.persistence.models.swarm import SubSwarm
from app.infrastructure.persistence.models.tenant import Tenant

EXECUTION_PROMPT_SUFFIX = (
    " Use Execution Studio policy: default simulate; live writes only after operator approval. "
    "Prefer free OAuth connectors (Notion, Gmail, GitHub). Never skip simulation before reporting."
)
DEPT_TOOLS: tuple[str, ...] = ("hive_memory_search", "task_list", "mcp_invoke")
SENTINEL_TOOLS: tuple[str, ...] = ("hive_memory_search", "task_list")

HiveTier = Literal["manager", "worker"]
ScheduleKind = Literal["interval", "cron"]
SwarmCategory = Literal["virtual_company", "sentinel", "personal"]

LIFE_OS_TOOLS: tuple[str, ...] = ("hive_memory_search", "task_list")


@dataclass(frozen=True, slots=True)
class _AgentSpec:
    name: str
    hive_tier: HiveTier
    system_prompt: str
    tools: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _RoutineSpec:
    name: str
    goal_template: str
    schedule_kind: ScheduleKind
    cron_expr: str | None = None
    interval_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class SwarmWizardSpec:
    template_id: str
    name: str
    swarm_name: str
    purpose: SwarmPurpose
    description: str
    accent_hex: str
    category: SwarmCategory
    department_id: str | None
    manager_slug: str
    super_router_preset: str | None
    agents: tuple[_AgentSpec, ...]
    routine: _RoutineSpec | None = None


def _exec(prompt: str) -> str:
    return f"{prompt}{EXECUTION_PROMPT_SUFFIX}"


SWARM_WIZARD_SPECS: dict[str, SwarmWizardSpec] = {
    "marketing-ops": SwarmWizardSpec(
        template_id="marketing-ops",
        name="Marketing Ops",
        swarm_name="Marketing Ops",
        purpose=SwarmPurpose.ACTION,
        description="Virtual Company marketing: campaign briefs, drafts, publish packs via Execution Studio.",
        accent_hex="#FF00AA",
        category="virtual_company",
        department_id="marketing",
        manager_slug="content_creation",
        super_router_preset="solo_app_actions",
        agents=(
            _AgentSpec("Marketing Manager", "manager", _exec("You are the marketing department manager."), DEPT_TOOLS),
            _AgentSpec("Topic Research Bee", "worker", _exec("Research topics from HiveMind and forager feeds."), DEPT_TOOLS),
            _AgentSpec("Content Draft Bee", "worker", _exec("Turn briefs into blog posts and social snippets."), DEPT_TOOLS),
            _AgentSpec("Publish Pack Bee", "worker", _exec("Stage publish packs in Notion and Gmail drafts via mcp_invoke."), DEPT_TOOLS),
        ),
        routine=_RoutineSpec(
            "Marketing ops cycle",
            "Run marketing ops: 3 researched topics, 1 verified long-form draft, 5 social snippets in Notion simulate mode.",
            "cron",
            cron_expr="0 9 * * 1,3,5",
        ),
    ),
    "lead-waterfall": SwarmWizardSpec(
        template_id="lead-waterfall",
        name="Sales Ops",
        swarm_name="Sales Ops",
        purpose=SwarmPurpose.ACTION,
        description="Virtual Company sales: lead waterfall with Gmail/Notion execution lane.",
        accent_hex="#00FFFF",
        category="virtual_company",
        department_id="sales",
        manager_slug="execution_operations",
        super_router_preset="solo_app_actions",
        agents=(
            _AgentSpec("Pipeline Manager", "manager", _exec("You are the sales pipeline manager."), DEPT_TOOLS),
            _AgentSpec("Lead Scout Bee", "worker", _exec("Discover and enrich leads from HiveMind."), DEPT_TOOLS),
            _AgentSpec("Outreach Draft Bee", "worker", _exec("Draft personalized outreach in Gmail simulate mode."), DEPT_TOOLS),
        ),
        routine=_RoutineSpec(
            "Daily sales waterfall",
            "Run sales waterfall: qualify leads, top 5 outreach drafts in Gmail simulate mode.",
            "cron",
            cron_expr="0 8 * * 1-5",
        ),
    ),
    "finance-ops": SwarmWizardSpec(
        template_id="finance-ops",
        name="Finance Ops",
        swarm_name="Finance Ops",
        purpose=SwarmPurpose.SCOUT,
        description="Virtual Company finance: read-only reports into Notion.",
        accent_hex="#FFB800",
        category="virtual_company",
        department_id="finance",
        manager_slug="review_quality",
        super_router_preset="solo_app_actions",
        agents=(
            _AgentSpec("Finance Manager", "manager", _exec("You are the finance controller — read-only reports only."), DEPT_TOOLS),
            _AgentSpec("Ledger Summary Bee", "worker", _exec("Aggregate figures from HiveMind notes."), DEPT_TOOLS),
            _AgentSpec("Report Pack Bee", "worker", _exec("Write finance report pages to Notion via mcp_invoke simulate."), DEPT_TOOLS),
        ),
        routine=_RoutineSpec(
            "Weekly finance snapshot",
            "Produce verified weekly finance snapshot in Notion simulate mode.",
            "cron",
            cron_expr="0 7 * * 1",
        ),
    ),
    "digital-ops": SwarmWizardSpec(
        template_id="digital-ops",
        name="Digital Ops",
        swarm_name="Digital Ops",
        purpose=SwarmPurpose.SCOUT,
        description="Virtual Company digital: UX research and conversion hypotheses in Notion.",
        accent_hex="#00E5FF",
        category="virtual_company",
        department_id="digital",
        manager_slug="research_intelligence",
        super_router_preset="solo_app_actions",
        agents=(
            _AgentSpec("Digital Manager", "manager", _exec("You are the digital/e-commerce manager."), DEPT_TOOLS),
            _AgentSpec("UX Research Bee", "worker", _exec("Audit flows and document UX findings."), DEPT_TOOLS),
            _AgentSpec("Conversion Ideas Bee", "worker", _exec("Propose A/B test ideas in Notion simulate mode."), DEPT_TOOLS),
        ),
        routine=_RoutineSpec(
            "Digital ops review",
            "Digital ops review: 3 UX findings, 2 conversion hypotheses in Notion simulate.",
            "cron",
            cron_expr="0 10 * * 2",
        ),
    ),
    "rnd-dev": SwarmWizardSpec(
        template_id="rnd-dev",
        name="R&D / Development",
        swarm_name="R&D Development",
        purpose=SwarmPurpose.ACTION,
        description="Virtual Company R&D: GitHub PR lane and opportunity research.",
        accent_hex="#00FF88",
        category="virtual_company",
        department_id="rnd",
        manager_slug="research_intelligence",
        super_router_preset="solo_dev_workspace",
        agents=(
            _AgentSpec("R&D Manager", "manager", _exec("You are R&D lead — PR-only workflow."), DEPT_TOOLS),
            _AgentSpec("Codebase Scout Bee", "worker", _exec("Inspect repo health and GitHub issue drafts via mcp_invoke."), DEPT_TOOLS),
            _AgentSpec("Opportunity Research Bee", "worker", _exec("Research mini-app opportunities from HiveMind."), DEPT_TOOLS),
        ),
        routine=_RoutineSpec(
            "R&D weekly scan",
            "R&D scan: tech debt notes, top 3 mini-app opportunities, GitHub issue drafts simulate.",
            "cron",
            cron_expr="0 11 * * 3",
        ),
    ),
    "product-ship": SwarmWizardSpec(
        template_id="product-ship",
        name="Product Ship",
        swarm_name="Product Ship",
        purpose=SwarmPurpose.ACTION,
        description="Virtual Company product: PRD planner and GitHub/Notion ship lane.",
        accent_hex="#9966FF",
        category="virtual_company",
        department_id="product",
        manager_slug="product_mission",
        super_router_preset="solo_dev_workspace",
        agents=(
            _AgentSpec("PRD Planner Manager", "manager", _exec("You are product manager."), DEPT_TOOLS),
            _AgentSpec("Tracer Bullet Bee", "worker", _exec("Decompose PRD slices into workflow steps."), DEPT_TOOLS),
            _AgentSpec("Kanban Slice Bee", "worker", _exec("Materialize workflow steps as Kanban child tasks."), DEPT_TOOLS),
            _AgentSpec("Ship Gate Bee", "worker", _exec("Run simulation checks and link slices to GitHub simulate."), DEPT_TOOLS),
        ),
        routine=_RoutineSpec(
            "Weekly ship review",
            "Product ship review: completed slices, Notion roadmap update simulate.",
            "cron",
            cron_expr="0 16 * * 5",
        ),
    ),
    "sentinel-radar": SwarmWizardSpec(
        template_id="sentinel-radar",
        name="Sentinel Radar",
        swarm_name="Sentinel Radar",
        purpose=SwarmPurpose.SCOUT,
        description="Read-only intelligence colony — no external API spend.",
        accent_hex="#66CCFF",
        category="sentinel",
        department_id=None,
        manager_slug="research_intelligence",
        super_router_preset=None,
        agents=(
            _AgentSpec(
                "Sentinel Manager",
                "manager",
                "You are the sentinel manager. Coordinate read-only scans; store verified signals in HiveMind.",
                SENTINEL_TOOLS,
            ),
            _AgentSpec("World Signals Bee", "worker", "Scan geopolitical and macro signals.", ("hive_memory_search",)),
            _AgentSpec("Trend Radar Bee", "worker", "Track industry trends from HiveMind.", ("hive_memory_search",)),
            _AgentSpec("Opportunity Scout Bee", "worker", "Identify mini-app opportunities.", SENTINEL_TOOLS),
        ),
        routine=_RoutineSpec(
            "Sentinel daily scan",
            (
                "Sentinel HiveMind learning scan: surface 3 verified AI/agent signals "
                "from free sources (RSS, Grokipedia, Wikipedia). "
                "Researcher drafts [INSIGHT] pages; critic verifies before hivemind-candidate ingest."
            ),
            "cron",
            cron_expr="0 6 * * *",
        ),
    ),
    "life-os": SwarmWizardSpec(
        template_id="life-os",
        name="Life OS",
        swarm_name="Life OS",
        purpose=SwarmPurpose.SCOUT,
        description="Overnight colony: dump ingest, graphify, task extraction, verified morning briefing.",
        accent_hex="#00FF88",
        category="personal",
        department_id=None,
        manager_slug="personal_life",
        super_router_preset=None,
        agents=(
            _AgentSpec(
                "Overnight Supervisor",
                "manager",
                _exec(
                    "You are an overnight life-OS supervisor. Triage dumps, prioritize stalled projects, "
                    "produce verified morning briefing only.",
                ),
                LIFE_OS_TOOLS,
            ),
            _AgentSpec(
                "Dump Ingest Bee",
                "worker",
                _exec(
                    "Ingest folder files and voice notes into hive memory. "
                    "Classify by project, urgency, and staleness.",
                ),
                LIFE_OS_TOOLS,
            ),
            _AgentSpec(
                "Task Extractor Bee",
                "worker",
                _exec(
                    "Extract actionable tasks from overnight ingest. "
                    "Link to graph nodes, dedupe, queue approval items.",
                ),
                LIFE_OS_TOOLS,
            ),
            _AgentSpec(
                "Morning Brief Bee",
                "worker",
                _exec(
                    "Compile morning summary: priorities, stalled projects, pollen earned, suggested next actions.",
                ),
                LIFE_OS_TOOLS,
            ),
        ),
        routine=_RoutineSpec(
            "Overnight dump & dream cycle",
            "Process overnight dump: graphify ingest, extract tasks, simulate outputs, deliver morning briefing.",
            "cron",
            cron_expr="0 6 * * *",
        ),
    ),
    "micro-saas-factory": SwarmWizardSpec(
        template_id="micro-saas-factory",
        name="Micro-SaaS Factory",
        swarm_name="Micro-SaaS Factory",
        purpose=SwarmPurpose.ACTION,
        description="Build landing + auth docs + checkout strategy + deploy recipe — simulate-first MVP factory.",
        accent_hex="#00FFFF",
        category="virtual_company",
        department_id="product",
        manager_slug="product_mission",
        super_router_preset="solo_dev_workspace",
        agents=(
            _AgentSpec(
                "Factory Supervisor",
                "manager",
                _exec(
                    "Orchestrate Micro-SaaS MVP factory: scope, landing, auth pattern, checkout strategy, deploy recipe. "
                    "Simulate every lane before live.",
                ),
                DEPT_TOOLS,
            ),
            _AgentSpec(
                "MVP Scope Bee",
                "worker",
                _exec("Define one-sharp-job MVP scope and 3–5 bee decomposition."),
                DEPT_TOOLS,
            ),
            _AgentSpec(
                "Landing Builder Bee",
                "worker",
                _exec("Draft public landing copy and magnet CTA — verified simulate only."),
                DEPT_TOOLS,
            ),
            _AgentSpec(
                "Auth Pattern Bee",
                "worker",
                _exec("Document JWT auth + tenant RBAC pattern for product users."),
                DEPT_TOOLS,
            ),
            _AgentSpec(
                "Deploy Recipe Bee",
                "worker",
                _exec("Produce docker-compose deploy recipe with health-check gate."),
                DEPT_TOOLS,
            ),
        ),
        routine=_RoutineSpec(
            "Micro-SaaS factory cycle",
            "Factory cycle: MVP scope → landing draft → auth doc → checkout checklist → deploy recipe.",
            "cron",
            cron_expr="0 14 * * 5",
        ),
    ),
}

VIRTUAL_COMPANY_TEMPLATE_IDS: frozenset[str] = frozenset(
    tid for tid, spec in SWARM_WIZARD_SPECS.items() if spec.category == "virtual_company"
)


def _build_local_memory(spec: SwarmWizardSpec) -> dict[str, Any]:
    """Mirror frontend buildSwarmLocalMemoryForTemplate."""

    if spec.category == "sentinel":
        return {
            "manager_slug": spec.manager_slug,
            "virtual_company_sentinel": True,
            "execution_studio": {
                "default_mode": "simulate",
                "live_requires_approval": True,
                "read_only": True,
            },
        }
    if spec.category == "personal":
        return {
            "manager_slug": spec.manager_slug,
            "life_os": True,
            "execution_studio": {
                "default_mode": "simulate",
                "live_requires_approval": True,
                "free_first_routing": True,
            },
            "dump_sleep_enabled": True,
            "auto_graphify_enabled": True,
        }
    dept_id = spec.department_id or ""
    connectors = list(DEPARTMENT_CONNECTOR_MAP.get(dept_id, ()))
    return {
        "virtual_company_department": dept_id,
        "manager_slug": spec.manager_slug,
        "execution_studio": {
            "default_mode": "simulate",
            "live_requires_approval": True,
            "free_first_routing": True,
            "super_router_preset": spec.super_router_preset,
            "suggested_connectors": connectors,
        },
    }


async def find_swarm_by_wizard_template(session: AsyncSession, *, template_id: str) -> SubSwarm | None:
    """Return active swarm whose local_memory.wizard_template matches."""

    key = template_id.strip().lower()
    stmt = select(SubSwarm).where(SubSwarm.is_active.is_(True)).order_by(SubSwarm.updated_at.desc()).limit(200)
    rows = list((await session.execute(stmt)).scalars().all())
    for row in rows:
        lm = row.local_memory if isinstance(row.local_memory, dict) else {}
        if str(lm.get("wizard_template") or "").strip().lower() == key:
            return row
    return None


async def list_built_wizard_templates(session: AsyncSession) -> list[str]:
    """Distinct wizard_template ids on active swarms."""

    stmt = select(SubSwarm).where(SubSwarm.is_active.is_(True)).limit(200)
    rows = list((await session.execute(stmt)).scalars().all())
    found: set[str] = set()
    for row in rows:
        lm = row.local_memory if isinstance(row.local_memory, dict) else {}
        raw = lm.get("wizard_template")
        if raw:
            found.add(str(raw).strip().lower())
    return sorted(found)


async def build_department_swarm(
    session: AsyncSession,
    *,
    tenant: Tenant,
    template_id: str,
    created_by_subject: str | None = None,
    skip_if_exists: bool = True,
) -> dict[str, Any]:
    """Build one wizard swarm + agents + optional routine (idempotent)."""

    key = template_id.strip().lower()
    spec = SWARM_WIZARD_SPECS.get(key)
    if spec is None:
        msg = f"unknown template_id:{key}"
        raise KeyError(msg)

    if skip_if_exists:
        existing = await find_swarm_by_wizard_template(session, template_id=key)
        if existing is not None:
            return {
                "status": "already_exists",
                "template_id": key,
                "swarm_id": str(existing.id),
                "agent_ids": [],
                "routine_id": None,
            }

    profile = profile_from_tenant(tenant)
    dept_memory = _build_local_memory(spec)
    profile_line = profile_context_block(profile)

    local_memory: dict[str, Any] = {
        "wizard_template": key,
        **dept_memory,
        "operator_profile": profile.model_dump() if profile.onboarded else None,
        "operator_profile_context": profile_line or None,
        "hive_ui": {
            "swarm_role_label": spec.name,
            "swarm_color_hex": spec.accent_hex,
            "manager_system_prompt": spec.description,
            "virtual_company": spec.department_id
            or ("sentinel" if spec.category == "sentinel" else ("personal" if spec.category == "personal" else None)),
        },
    }

    swarm = await create_sub_swarm(
        session,
        name=spec.swarm_name,
        purpose=spec.purpose,
        local_memory=local_memory,
        queen_agent_id=None,
        is_active=True,
    )

    agent_ids: list[str] = []
    exec_studio = dept_memory.get("execution_studio")
    for agent_spec in spec.agents:
        try:
            agent = await create_agent_record(
                session,
                name=agent_spec.name,
                role=AgentRole.LEARNER,
                status=AgentStatus.IDLE,
                swarm_id=swarm.id,
                config={"origin": "virtual_company_wizard", "hive_tier": agent_spec.hive_tier},
            )
        except AgentCatalogError as exc:
            msg = str(exc)
            raise ValueError(msg) from exc

        output_config: dict[str, Any] = {
            "hive_tier": agent_spec.hive_tier,
            "wizard_template": key,
            "virtual_company_department": spec.department_id,
            "execution_studio": exec_studio,
        }
        cfg = AgentConfig(
            agent_id=agent.id,
            system_prompt=agent_spec.system_prompt,
            user_prompt_template="",
            tools=list(agent_spec.tools),
            output_format="text",
            output_destination="dashboard",
            output_config=output_config,
            schedule_type="on_demand",
            schedule_value=None,
            is_active=True,
        )
        session.add(cfg)
        await session.flush()
        agent_ids.append(str(agent.id))

    routine_id: str | None = None
    if spec.routine is not None:
        routine = await create_supervisor_routine(
            session,
            name=spec.routine.name,
            goal_template=spec.routine.goal_template,
            created_by_subject=created_by_subject,
            schedule_kind=spec.routine.schedule_kind,
            interval_seconds=spec.routine.interval_seconds,
            cron_expr=spec.routine.cron_expr,
            runtime_mode="durable",
            roles=[],
            retrieval_contract=None,
            skills=["execution-studio"],
            context_payload={
                "wizard_template": key,
                "swarm_id": str(swarm.id),
                "virtual_company_department": spec.department_id,
                "execution_studio": exec_studio,
            },
            tenant_id=tenant.id,
        )
        routine_id = str(routine.id)

    await session.commit()
    return {
        "status": "created",
        "template_id": key,
        "swarm_id": str(swarm.id),
        "agent_ids": agent_ids,
        "routine_id": routine_id,
    }


async def build_all_virtual_company_swarms(
    session: AsyncSession,
    *,
    tenant: Tenant,
    created_by_subject: str | None = None,
    include_sentinel: bool = True,
) -> list[dict[str, Any]]:
    """Build all department swarms (+ optional sentinel)."""

    template_ids = sorted(VIRTUAL_COMPANY_TEMPLATE_IDS)
    if include_sentinel:
        template_ids.append("sentinel-radar")
    results: list[dict[str, Any]] = []
    for tid in template_ids:
        row = await build_department_swarm(
            session,
            tenant=tenant,
            template_id=tid,
            created_by_subject=created_by_subject,
            skip_if_exists=True,
        )
        results.append(row)
    return results


__all__ = [
    "SWARM_WIZARD_SPECS",
    "VIRTUAL_COMPANY_TEMPLATE_IDS",
    "build_all_virtual_company_swarms",
    "build_department_swarm",
    "find_swarm_by_wizard_template",
    "list_built_wizard_templates",
]
