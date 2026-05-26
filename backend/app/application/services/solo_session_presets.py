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
            "Paper trading cockpit review (žiadne live peniaze).\n\n"
            "Prečítaj posledný paper trading stav a navrhni:\n"
            "- 3 pozorovania z posledných signálov\n"
            "- 1 risk flag ak existuje\n"
            "- odporúčanie: hold / adjust paper params / skip\n\n"
            "Simulate-first; live trading explicitne zakázané bez operátorského OK."
        ),
        roles=["researcher", "critic"],
        skills=["context", "execution-studio"],
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
