"""Execution Studio operator + agent manual — single source for UI and agent skills."""

from __future__ import annotations

from typing import Any, Literal

ManualAudience = Literal["operator", "agent", "both"]

MANUAL_VERSION = "1.0.0"

EXECUTION_STUDIO_MANUAL_SECTIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "overview",
        "title": "What is Execution Studio?",
        "audience": "both",
        "order": 1,
        "summary": "Product layer connecting external apps and internal codebase execution under one governed policy.",
        "content_md": (
            "Execution Studio sits on top of the Dynamic Connector Hub, OAuth vault, Queen Maintainer, "
            "and supervisor sessions. Operators connect SaaS tools and repo connectors; agents execute "
            "tasks in **draft**, **simulate**, or **live** modes. Nothing reaches production without "
            "simulation and approval gates where configured."
        ),
    },
    {
        "id": "execution_modes",
        "title": "Execution modes (draft → simulate → live)",
        "audience": "both",
        "order": 2,
        "summary": "Three modes govern every external tool call and codebase PR.",
        "content_md": (
            "| Mode | External tools | Codebase (PR) |\n"
            "|------|----------------|---------------|\n"
            "| **Draft** | Preview args only, no HTTP | Preview branch + paths, no GitHub |\n"
            "| **Simulate** | Read calls may run; writes dry-run | Paths validated against denylist |\n"
            "| **Live** | Real upstream HTTP | Opens GitHub PR on `queen-maintainer/*` |\n\n"
            "Default for new tenants: **simulate**. Live write/publish/financial external actions "
            "require supervisor approval when `live_requires_approval` is enabled. Live codebase PRs "
            "require operator confirmation when `live_codebase_requires_approval` is enabled."
        ),
        "steps": (
            {"step": 1, "action": "Start in Draft", "detail": "Validate plan and arguments without side effects."},
            {"step": 2, "action": "Run Simulate", "detail": "Dry-run writes; optional read probes for external APIs."},
            {"step": 3, "action": "Go Live", "detail": "Only after operator approval and active connectors."},
        ),
    },
    {
        "id": "external_lane",
        "title": "External lane — connect SaaS & media tools",
        "audience": "both",
        "order": 3,
        "summary": "Marketplace templates, OAuth, and governed mcp_invoke for outbound apps.",
        "content_md": (
            "1. **Install** a Phase 3 template from Tools Marketplace.\n"
            "2. **Connect credentials** via OAuth consent or API key in Connector Hub.\n"
            "3. **Test upstream** — successful test activates the connector.\n"
            "4. **Assign manager lanes** or Super Tool Routers so supervisor bees inherit allowlists.\n"
            "5. **Execute** via supervisor task or Execution Studio dry-run.\n\n"
            "Use **App routers** (Composio, Nango, Merge) when you need many OAuth SaaS apps without "
            "building one connector per vendor. Use **Media** pack (Venice, Monid) for image/copy generation."
        ),
        "steps": (
            {"step": 1, "action": "Install template", "detail": "Marketplace → Connect → Configure → Test → Activate."},
            {"step": 2, "action": "Wire agents", "detail": "Super Tool Router or manager allowlist on the swarm."},
            {"step": 3, "action": "Run task", "detail": "Supervisor session with tool-capable sub-roles."},
        ),
    },
    {
        "id": "internal_codebase",
        "title": "SCV — internal codebase lane (Queen Maintainer PRs)",
        "audience": "both",
        "order": 4,
        "summary": "PR-only changes to this repository; denylist protects secrets and prod config.",
        "content_md": (
            "SCV (internal codebase agent) hands approved work to Queen Maintainer: **researcher → coder → critic** "
            "with skills `queen-maintainer`, `tdd`, `self-review-loop`. It never commits directly to main — only opens "
            "PRs on `queen-maintainer/*` branches via the `github_rest` connector.\n\n"
            "**Denylist** blocks `.env*`, billing routers, `docker-compose.prod`, nginx TLS, and "
            "`backend/app/core/config.py`. Operators merge PRs manually after CI passes.\n\n"
            "Enable `QUEEN_MAINTAINER_GITHUB_OWNER/REPO`, connect `github_rest`, then use "
            "**Run Queen Maintainer** or approve a **codebase_execution** initiative proposal."
        ),
        "steps": (
            {"step": 1, "action": "Connect github_rest", "detail": "Marketplace install + token + test."},
            {"step": 2, "action": "Configure repo env", "detail": "QUEEN_MAINTAINER_GITHUB_OWNER and _REPO."},
            {"step": 3, "action": "Run Maintainer", "detail": "Execution Studio → Run Queen Maintainer."},
            {"step": 4, "action": "Review PR", "detail": "Operator merges after CI — agents never merge."},
        ),
    },
    {
        "id": "research_to_execution",
        "title": "Research → approval → execution handoff",
        "audience": "both",
        "order": 5,
        "summary": "How optimization research becomes a Maintainer run after operator approval.",
        "content_md": (
            "1. **Research agent** completes analysis and raises a `codebase_execution` initiative "
            "proposal (or operator submits via Execution Studio).\n"
            "2. Proposal includes goal excerpt, suggested paths, and risk tier — always **pending** until reviewed.\n"
            "3. **Operator approves** in Agents → Suggestions or Execution Studio pending queue.\n"
            "4. **Handoff** automatically queues a Queen Maintainer supervisor session with the "
            "approved proposal injected into the goal.\n"
            "5. Maintainer produces tracer bullets, tests, and opens a PR — operator merges.\n\n"
            "External research deliverables (Notion, Gmail drafts) use the **external lane** instead."
        ),
        "steps": (
            {"step": 1, "action": "Research completes", "detail": "Proposal type `codebase_execution` created."},
            {"step": 2, "action": "Operator approves", "detail": "Initiative review or Studio handoff confirm."},
            {"step": 3, "action": "Maintainer runs", "detail": "Supervisor session with injected goal."},
            {"step": 4, "action": "PR + merge", "detail": "Human merges; recipe saved on verified outcome."},
        ),
    },
    {
        "id": "agent_reference",
        "title": "Agent quick reference",
        "audience": "agent",
        "order": 6,
        "summary": "Rules bees must follow when executing via Execution Studio.",
        "content_md": (
            "- **Always** prefer API connectors over browser automation.\n"
            "- **Never** skip simulation before reporting success to the operator.\n"
            "- **Never** modify denylist paths or production secrets.\n"
            "- Use `mcp_invoke` only for connectors on your manager allowlist.\n"
            "- For codebase work: produce minimal diffs, run tests, open PR — do not merge.\n"
            "- Fetch this manual via `GET /api/v1/execution-studio/manual` when planning execution steps.\n"
            "- Proposal type for repo changes: `codebase_execution` with payload "
            "`execution_domain: internal_codebase`."
        ),
    },
    {
        "id": "troubleshooting",
        "title": "Troubleshooting",
        "audience": "operator",
        "order": 7,
        "summary": "Common blockers and fixes.",
        "content_md": (
            "| Symptom | Fix |\n"
            "|---------|-----|\n"
            "| `needs_credentials` | Complete OAuth or seal API key; run vault sync via test. |\n"
            "| `connector_inactive` | POST test on connector row to activate. |\n"
            "| `approval_required` | Approve supervisor session or confirm live in Studio. |\n"
            "| `denylist_blocked` | Path forbidden — choose a safe file outside denylist. |\n"
            "| Maintainer disabled | Set `QUEEN_MAINTAINER_ENABLED=true` in deployment env. |\n"
            "| PR manual_required | Configure GITHUB_OWNER/REPO and active github_rest connector. |"
        ),
    },
)


def build_execution_studio_manual(*, section_id: str | None = None) -> dict[str, Any]:
    """Return full manual or one section for UI and agent consumption.

    Args:
        section_id: Optional section slug; when set returns a single section envelope.

    Returns:
        Structured manual dict safe for JSON serialization.
    """

    sections = sorted(EXECUTION_STUDIO_MANUAL_SECTIONS, key=lambda row: int(row.get("order") or 0))
    if section_id:
        cleaned = section_id.strip().lower()
        match = next((sec for sec in sections if str(sec.get("id") or "") == cleaned), None)
        if match is None:
            return {"version": MANUAL_VERSION, "found": False, "section": None}
        return {"version": MANUAL_VERSION, "found": True, "section": dict(match)}

    return {
        "version": MANUAL_VERSION,
        "title": "Execution Studio Manual",
        "api_path": "/api/v1/execution-studio/manual",
        "agent_skill": "execution-studio",
        "summary": (
            "Governed external app execution and internal codebase PR workflow for Queenswarm operators and agents."
        ),
        "sections": [dict(sec) for sec in sections],
        "flows": [
            {
                "id": "external_saas",
                "label": "External SaaS execution",
                "section_ids": ["overview", "execution_modes", "external_lane"],
            },
            {
                "id": "internal_codebase",
                "label": "Internal codebase / SCV",
                "section_ids": ["internal_codebase", "research_to_execution"],
            },
        ],
        "agent_quick_reference": next(
            (str(sec.get("content_md") or "") for sec in sections if sec.get("id") == "agent_reference"),
            "",
        ),
    }


__all__ = ["MANUAL_VERSION", "build_execution_studio_manual"]
