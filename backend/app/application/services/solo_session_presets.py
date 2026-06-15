"""Solo operator supervisor session goal presets — Bank PO, marketing, trading."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings


class SoloSessionPresetOut(BaseModel):
    """One quick-start goal template for /agents supervisor sessions."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    lane: str
    goal: str
    runtime_mode: str = "durable"
    roles: list[str] = Field(default_factory=lambda: ["researcher", "critic"])
    retrieval_contract: str = "default_v2"
    skills: list[str] = Field(default_factory=lambda: ["context", "execution-studio"])


_BANK_PO_GUARDRAIL = (
    "Nikdy neposielaj do LLM citlivé bank dáta, PII, interné čísla účtov ani nepublic roadmapy. "
    "Pracuj len s anonymizovanými / verejnými podkladmi od operátora."
)

SOLO_SESSION_PRESETS: dict[str, SoloSessionPresetOut] = {
    "bank-po-brief": SoloSessionPresetOut(
        id="bank-po-brief",
        label="Bank PO — stakeholder brief",
        lane="po",
        goal=(
            "Bank PO supervisor brief (verify-first).\n\n"
            "Priprav stakeholder brief zo anonymizovaných podkladov operátora:\n"
            "- Status a wins (max 5 bodov)\n"
            "- Riziká a blockery\n"
            "- Konkrétne asks pre stakeholderov\n"
            "- Odporúčané rozhodnutia na ďalší týždeň\n\n"
            f"{_BANK_PO_GUARDRAIL}\n"
            "Researcher draft → critic APPROVE → operator_reply po slovensky (≤400 slov)."
        ),
    ),
    "bank-po-backlog": SoloSessionPresetOut(
        id="bank-po-backlog",
        label="Bank PO — backlog review",
        lane="po",
        goal=(
            "Bank PO backlog refinement (verify-first).\n\n"
            "Z anonymizovaného backlogu / PI plánu operátora:\n"
            "1. Top 5 priorít s odôvodnením\n"
            "2. Závislosti a cross-team blockery\n"
            "3. Návrh reorder alebo scope cut (ak treba)\n"
            "4. Open questions pre operátora\n\n"
            f"{_BANK_PO_GUARDRAIL}\n"
            "Critic musí overiť konzistenciu pred finálnym výstupom."
        ),
    ),
    "marketing-draft": SoloSessionPresetOut(
        id="marketing-draft",
        label="Marketing — content draft",
        lane="marketing",
        goal=(
            "Marketing content draft pre Publish Queue (simulate-first).\n\n"
            "Vytvor 1 publish pack JSON (channel, title, body, media_url ak je) pre queenswarm.love.\n"
            "- simulate_only=true\n"
            "- žiadne API kľúče ani interné URL v texte\n"
            "- critic verify pred odporúčaním approve\n\n"
            "Operator_reply: stručný SK súhrn + odkaz na Execution Studio publish queue."
        ),
        skills=["context", "execution-studio", "publish_pack"],
    ),
    "paper-trading-review": SoloSessionPresetOut(
        id="paper-trading-review",
        label="Trading — paper review",
        lane="trading",
        goal=(
            "Paper trading cockpit review (no live money).\n\n"
            "Read the latest paper trading state and propose:\n"
            "- 3 observations from recent signals\n"
            "- 1 risk flag if any\n"
            "- recommendation: hold / adjust paper params / skip\n\n"
            "Simulate-first; live trading forbidden without explicit operator OK."
        ),
        roles=["researcher", "critic"],
        skills=["context", "execution-studio"],
    ),
    "trading-thesis": SoloSessionPresetOut(
        id="trading-thesis",
        label="Trading — thesis brief",
        lane="trading",
        goal=(
            "PROJECT: Trading thesis brief (probabilities not guesses — verify-first).\n\n"
            "Complete these sections before any live stake:\n"
            "1. Market / event — platform, resolution, liquidity\n"
            "2. Implied probability — market mid-price or order book derivation\n"
            "3. Your edge — evidence-backed disagreement with market\n"
            "4. Position size cap — hard $ or % portfolio limit\n"
            "5. Kill criteria — exit triggers (price, news, time)\n"
            "6. Paper preflight — simulated session link or gaps\n\n"
            "Deliverables:\n"
            "- Structured thesis markdown\n"
            "- polymarket-prediction-evaluator score vs implied prob\n"
            "- real-money-risk-gate checklist (live blocked until operator OK)\n"
            "- Critic APPROVE before operator summary (≤400 words)\n\n"
            "Simulate-first — no live orders in this session."
        ),
        roles=["researcher", "critic"],
        skills=[
            "polymarket-prediction-evaluator",
            "real-money-risk-gate",
            "decision-frameworks",
        ],
        retrieval_contract="customer_history+policy+last_3_tasks",
    ),
    "web-redesign-discovery": SoloSessionPresetOut(
        id="web-redesign-discovery",
        label="Web redesign — discovery",
        lane="ops",
        goal=(
            "PROJECT: Web Redesign — Phase 1 Discovery (verify-first).\n\n"
            "Deliverables:\n"
            "1. Audit current site UX, SEO, and speed from public sources.\n"
            "2. Benchmark 5 competitors.\n"
            "3. Proposed IA (max 12 pages) + MVP priorities.\n"
            "4. Three homepage concept outlines (text).\n\n"
            "Output: English report, max 1500 words.\n"
            "Critic APPROVE before final. Simulate only."
        ),
        roles=["researcher", "designer", "critic"],
        skills=["context", "decide", "tdd"],
    ),
    "marketing-campaign": SoloSessionPresetOut(
        id="marketing-campaign",
        label="Marketing — campaign brief",
        lane="marketing",
        goal=(
            "PROJECT: Marketing campaign brief (simulate-first).\n\n"
            "Deliverables:\n"
            "1. Audience + positioning (1 paragraph each)\n"
            "2. Channel plan (3 channels max)\n"
            "3. Content calendar skeleton (2 weeks)\n"
            "4. Draft publish pack JSON for simulate queue\n\n"
            "No live posts. Critic verify before recommending approve."
        ),
        skills=["context", "execution-studio", "publish_pack"],
    ),
    "investment-product-brief": SoloSessionPresetOut(
        id="investment-product-brief",
        label="Investments — product brief",
        lane="investments",
        goal=(
            "PROJECT: Investment / product brief (verify-first).\n\n"
            "Complete these sections (anonymized — no bank PII):\n"
            "1. Problem — pain or opportunity\n"
            "2. Audience — segments who benefit\n"
            "3. KPI — leading + lagging success metrics\n"
            "4. Regulatory notes — compliance constraints (no internal policy numbers)\n"
            "5. Open questions — unknowns for stakeholder grill\n"
            "6. Sources to fetch — public URLs or operator-provided docs\n\n"
            "Deliverables:\n"
            "- Structured brief markdown (SK or EN per operator)\n"
            "- 3 HiveMind recall bullets with citations\n"
            "- grill-me follow-up questions (max 5) if gaps remain\n"
            "- Critic APPROVE before final operator_reply (≤400 words)\n\n"
            f"{_BANK_PO_GUARDRAIL}\n"
            "Use Research Bee + simulate-first. Dispatch to Kanban when done."
        ),
        roles=["researcher", "critic"],
        skills=["grill-me", "decision-frameworks", "business-strategy-simulator"],
        retrieval_contract="customer_history+policy+last_3_tasks",
    ),
    "competitor-research": SoloSessionPresetOut(
        id="competitor-research",
        label="Research — competitor intel",
        lane="ops",
        goal=(
            "PROJECT: Competitor research sprint (verify-first).\n\n"
            "Deliverables:\n"
            "1. Top 5 competitors — product, pricing signal, positioning\n"
            "2. Gap analysis vs our offer\n"
            "3. 5 actionable recommendations ranked by impact\n\n"
            "Public sources only. Critic APPROVE. Simulate only."
        ),
        roles=["researcher", "critic"],
        skills=["context", "decide", "tdd", "competitor-scrape-analyze"],
    ),
    "lead-gen-lane": SoloSessionPresetOut(
        id="lead-gen-lane",
        label="Lead Gen Lane — scout + outreach",
        lane="sales",
        goal=(
            "PROJECT: Lead Gen Lane (simulate-first — Verified recipe LEAD_GEN_LANE).\n\n"
            "ICP (fill in before run):\n"
            "- Industry: ___\n"
            "- Company size: ___\n"
            "- Region: ___\n"
            "- Signal (hiring, funding, tool stack): ___\n\n"
            "Deliverables:\n"
            "1. ICP summary from curated memory + Wiki forager-insights\n"
            "2. Lead Scout — ≤10 qualified leads from HiveMind (tag: lead). Never invent emails.\n"
            "3. Optional: 3 competitor intel bullets (public sources)\n"
            "4. Outreach Draft Bee — ≤5 personalised messages (subject + body + CTA)\n"
            "5. Critic APPROVE + operator report (SK or EN, ≤400 words)\n\n"
            "Gmail simulate_only=true. No live send. Persist outreach-result tags."
        ),
        roles=["researcher", "designer", "critic"],
        skills=["context", "decide", "lead-gen-lane", "competitor-scrape-analyze"],
        retrieval_contract="wiki_only",
    ),
}


def list_solo_session_presets() -> list[SoloSessionPresetOut]:
    """Return session presets when solo mode is enabled."""

    if not settings.solo_mode_enabled and not settings.operator_loop_enabled:
        return []
    return list(SOLO_SESSION_PRESETS.values())


def get_solo_session_preset(preset_id: str) -> SoloSessionPresetOut | None:
    """Resolve one preset by id."""

    return SOLO_SESSION_PRESETS.get(preset_id.strip())


__all__ = [
    "SOLO_SESSION_PRESETS",
    "SoloSessionPresetOut",
    "get_solo_session_preset",
    "list_solo_session_presets",
]
