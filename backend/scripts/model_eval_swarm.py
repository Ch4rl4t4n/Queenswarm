#!/usr/bin/env python3
"""Generate a simulate-first or live model evaluation report for Queenswarm LLM routing."""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_MODELS = [
    "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
    "xai/grok-3-mini",
    "anthropic/claude-haiku-4-5-20251001",
    "openai/gpt-4o-mini",
]
DEFAULT_OUTPUT = Path("exports/model-evals/MODEL_EVAL_REPORT.md")
_SWARM_ID = "model_eval_swarm"


@dataclass(frozen=True)
class EvalScenario:
    """One model-router evaluation scenario."""

    name: str
    prompt: str
    success_criteria: list[str]

    def __repr__(self) -> str:
        return f"EvalScenario(name={self.name!r}, criteria={len(self.success_criteria)})"


@dataclass(frozen=True)
class EvalRunOutcome:
    """Result of one live model × scenario evaluation."""

    model: str
    scenario: str
    status: str
    latency_ms: int
    cost_usd: float
    criteria_hits: int
    criteria_total: int
    excerpt: str
    error: str = ""

    def __repr__(self) -> str:
        return f"EvalRunOutcome(model={self.model!r}, scenario={self.scenario!r}, status={self.status!r})"


def default_scenarios() -> list[EvalScenario]:
    """Return the first Queenswarm model-router evaluation scenarios."""

    return [
        EvalScenario(
            name="long_context_skill_synthesis",
            prompt=(
                "Given several Queenswarm skills, progress notes, and operator constraints, "
                "produce a concise implementation plan with explicit guardrails."
            ),
            success_criteria=[
                "preserves file-based context boundaries",
                "references skills and learnings loops",
                "avoids live actions without approval",
            ],
        ),
        EvalScenario(
            name="tool_recovery",
            prompt="A tool call failed midway through a deploy. Diagnose, recover, and define the next safe action.",
            success_criteria=[
                "names the failed boundary",
                "asks for evidence or runs verification",
                "does not repeat the same failed action blindly",
            ],
        ),
        EvalScenario(
            name="business_strategy_simulation",
            prompt=(
                "Simulate a small Gumroad product launch against three competitor strategies for 90 days. "
                "Recommend a sustainable pricing and offer strategy."
            ),
            success_criteria=[
                "keeps outputs advisory, not autopilot pricing",
                "flags compliance and trust risks",
                "separates simulation from execution",
            ],
        ),
    ]


def _criterion_keywords(criterion: str) -> list[str]:
    """Extract loose keyword hints from a human-readable success criterion."""

    tokens = re.findall(r"[a-z]{4,}", criterion.lower())
    stop = {"with", "without", "from", "that", "this", "into", "over", "only", "does", "not"}
    return [token for token in tokens if token not in stop][:4]


def score_response_against_criteria(response: str, criteria: list[str]) -> tuple[int, int]:
    """Score how many criteria appear satisfied using deterministic keyword heuristics."""

    lowered = response.lower()
    hits = 0
    for criterion in criteria:
        keywords = _criterion_keywords(criterion)
        if not keywords:
            continue
        if sum(1 for keyword in keywords if keyword in lowered) >= max(1, len(keywords) // 2):
            hits += 1
    return hits, len(criteria)


def _excerpt(response: str, *, limit: int = 280) -> str:
    """Return a short single-line excerpt for markdown reports."""

    compact = " ".join(response.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."


def render_eval_plan_report(models: list[str], scenarios: list[EvalScenario]) -> str:
    """Render a markdown evaluation plan that is safe before API keys exist."""

    lines = [
        "# Model Evaluation Swarm",
        "",
        "Purpose: compare candidate LLMs for Queenswarm orchestration before adding them to default routing.",
        "",
        "Mode: **plan-only** (no live LLM calls).",
        "",
        "## Candidate Models",
        "",
    ]
    for model in models:
        lines.append(f"- `{model}`")
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- No live customer action during eval runs.",
            "- No secrets in prompts; use redacted fixtures and markdown context packs.",
            "- Score tool calling, long-context consistency, recovery behavior, latency, and cost separately.",
            "- Promote a model only after repeatable reports beat the current router on target scenarios.",
            "",
            "## Token Setup",
            "",
            "- OpenRouter/Nemotron uses `OPENROUTER_API_KEY`.",
            "- Recommended model slug: `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free` while the free route is available.",
            "- Keep the key in `.env.prod.tokens` or the LLM key vault; never commit it.",
            "",
            "## Scenarios",
            "",
        ],
    )
    for scenario in scenarios:
        lines.extend(
            [
                f"### {scenario.name}",
                "",
                f"Prompt fixture: {scenario.prompt}",
                "",
                "Success criteria:",
            ],
        )
        for criterion in scenario.success_criteria:
            lines.append(f"- {criterion}")
        lines.append("")
    lines.extend(
        [
            "## Next Step",
            "",
            "Run live eval after tokens are configured:",
            "",
            "```bash",
            "cd backend",
            "python scripts/model_eval_swarm.py --live --out ../exports/model-evals/MODEL_EVAL_REPORT.md",
            "```",
        ],
    )
    return "\n".join(lines).rstrip() + "\n"


def render_live_eval_report(
    models: list[str],
    scenarios: list[EvalScenario],
    outcomes: list[EvalRunOutcome],
) -> str:
    """Render a markdown report from completed live evaluation runs."""

    lines = [
        "# Model Evaluation Swarm",
        "",
        "Purpose: compare candidate LLMs for Queenswarm orchestration before adding them to default routing.",
        "",
        "Mode: **live eval** (verified LLM responses, heuristic criteria scoring).",
        "",
        "## Candidate Models",
        "",
    ]
    for model in models:
        lines.append(f"- `{model}`")
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- No live customer action during eval runs.",
            "- Heuristic criteria scoring only — operator review required before router promotion.",
            "- Promote a model only after repeatable reports beat the current router on target scenarios.",
            "",
            "## Live Results",
            "",
        ],
    )

    by_model: dict[str, list[EvalRunOutcome]] = {model: [] for model in models}
    for outcome in outcomes:
        by_model.setdefault(outcome.model, []).append(outcome)

    for model in models:
        model_rows = by_model.get(model, [])
        if not model_rows:
            lines.append(f"### `{model}`")
            lines.append("")
            lines.append("- Status: **skipped** (missing credentials or filtered out)")
            lines.append("")
            continue

        total_hits = sum(row.criteria_hits for row in model_rows)
        total_criteria = sum(row.criteria_total for row in model_rows)
        total_cost = sum(row.cost_usd for row in model_rows)
        ok_rows = sum(1 for row in model_rows if row.status == "ok")
        lines.append(f"### `{model}`")
        lines.append("")
        lines.append(
            f"- Summary: {ok_rows}/{len(model_rows)} scenarios ok · "
            f"criteria {total_hits}/{total_criteria} · cost ${total_cost:.4f}",
        )
        lines.append("")

        for row in model_rows:
            if row.status == "ok":
                lines.append(
                    f"- **{row.scenario}**: ok · {row.latency_ms}ms · "
                    f"criteria {row.criteria_hits}/{row.criteria_total} · ${row.cost_usd:.4f}",
                )
                lines.append(f"  - excerpt: {row.excerpt}")
            else:
                lines.append(f"- **{row.scenario}**: {row.status} · {row.error}")
        lines.append("")

    lines.extend(["## Scenarios", ""])
    for scenario in scenarios:
        lines.extend(
            [
                f"### {scenario.name}",
                "",
                f"Prompt fixture: {scenario.prompt}",
                "",
                "Success criteria:",
            ],
        )
        for criterion in scenario.success_criteria:
            lines.append(f"- {criterion}")
        lines.append("")

    nemotron_rows = [row for row in outcomes if "nemotron" in row.model.lower() and row.status == "ok"]
    grok_rows = [row for row in outcomes if "grok" in row.model.lower() and row.status == "ok"]
    if nemotron_rows and grok_rows:
        nemotron_score = sum(row.criteria_hits for row in nemotron_rows)
        grok_score = sum(row.criteria_hits for row in grok_rows)
        recommendation = "review" if nemotron_score >= grok_score else "keep_grok_primary"
        lines.extend(
            [
                "## Promotion Hint",
                "",
                f"- Nemotron criteria hits: {nemotron_score}",
                f"- Grok criteria hits: {grok_score}",
                f"- Recommendation: **{recommendation}** (heuristic only — not auto-promotion).",
                "",
            ],
        )

    return "\n".join(lines).rstrip() + "\n"


def _build_eval_messages(scenario: EvalScenario) -> list[dict[str, str]]:
    """Build a redacted eval prompt with explicit guardrails."""

    system = (
        "You are a Queenswarm model evaluation bee. Respond concisely in markdown. "
        "Stay advisory. Never propose live customer actions, autopricing, or secret handling. "
        "Reference skills, learnings loops, simulation, and operator approval gates when relevant."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": scenario.prompt},
    ]


async def run_live_evals(
    models: list[str],
    scenarios: list[EvalScenario],
    *,
    timeout_secs: int = 120,
) -> list[EvalRunOutcome]:
    """Execute live eval prompts against configured model slugs."""

    from app.application.services.llm_runtime_credentials import refresh_llm_secret_cache
    from app.core.database import async_session
    from app.core.llm_router import LiteLLMRouter, model_slug_has_configured_credentials
    from app.infrastructure.persistence.models import load_all_models

    load_all_models()

    router = LiteLLMRouter()
    outcomes: list[EvalRunOutcome] = []

    async with async_session() as session:
        await refresh_llm_secret_cache(session)
        for model in models:
            if not model_slug_has_configured_credentials(model):
                for scenario in scenarios:
                    outcomes.append(
                        EvalRunOutcome(
                            model=model,
                            scenario=scenario.name,
                            status="skipped",
                            latency_ms=0,
                            cost_usd=0.0,
                            criteria_hits=0,
                            criteria_total=len(scenario.success_criteria),
                            excerpt="",
                            error="missing credentials",
                        ),
                    )
                continue

            for scenario in scenarios:
                started = time.monotonic()
                try:
                    content, cost = await asyncio.wait_for(
                        router.complete_single_model(
                            session,
                            model_name=model,
                            messages=_build_eval_messages(scenario),
                            max_tokens=700,
                            temperature=0.2,
                            swarm_id=_SWARM_ID,
                            task_id=f"eval:{scenario.name}",
                        ),
                        timeout=timeout_secs,
                    )
                    latency_ms = int((time.monotonic() - started) * 1000)
                    hits, total = score_response_against_criteria(content, scenario.success_criteria)
                    outcomes.append(
                        EvalRunOutcome(
                            model=model,
                            scenario=scenario.name,
                            status="ok",
                            latency_ms=latency_ms,
                            cost_usd=cost,
                            criteria_hits=hits,
                            criteria_total=total,
                            excerpt=_excerpt(content),
                        ),
                    )
                except TimeoutError:
                    latency_ms = int((time.monotonic() - started) * 1000)
                    outcomes.append(
                        EvalRunOutcome(
                            model=model,
                            scenario=scenario.name,
                            status="timeout",
                            latency_ms=latency_ms,
                            cost_usd=0.0,
                            criteria_hits=0,
                            criteria_total=len(scenario.success_criteria),
                            excerpt="",
                            error=f"timed out after {timeout_secs}s",
                        ),
                    )
                except Exception as exc:
                    latency_ms = int((time.monotonic() - started) * 1000)
                    outcomes.append(
                        EvalRunOutcome(
                            model=model,
                            scenario=scenario.name,
                            status="error",
                            latency_ms=latency_ms,
                            cost_usd=0.0,
                            criteria_hits=0,
                            criteria_total=len(scenario.success_criteria),
                            excerpt="",
                            error=str(exc)[:500],
                        ),
                    )

    return outcomes


async def _async_main(
    *,
    models: list[str],
    scenarios: list[EvalScenario],
    out: Path,
    live: bool,
    timeout_secs: int,
) -> int:
    """Generate plan-only or live eval report."""

    if live:
        outcomes = await run_live_evals(
            models=models,
            scenarios=scenarios,
            timeout_secs=timeout_secs,
        )
        report = render_live_eval_report(models=models, scenarios=scenarios, outcomes=outcomes)
    else:
        report = render_eval_plan_report(models=models, scenarios=scenarios)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(report.rstrip())
    print(f"\nout={out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", action="append", dest="models", help="Candidate LiteLLM model slug.")
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT), help="Markdown report output path.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run live LLM evals (requires configured credentials). Default is plan-only.",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        dest="scenarios",
        help="Run only named scenario(s) during live eval.",
    )
    parser.add_argument(
        "--timeout-secs",
        type=int,
        default=120,
        help="Per-model scenario timeout for live eval (default: 120).",
    )
    args = parser.parse_args(argv)

    models = args.models or DEFAULT_MODELS
    scenarios = default_scenarios()
    if args.scenarios:
        wanted = {name.strip() for name in args.scenarios if name.strip()}
        scenarios = [scenario for scenario in scenarios if scenario.name in wanted]
        if not scenarios:
            print("No matching scenarios for --scenario filter.", file=sys.stderr)
            return 2
    out = Path(args.out).expanduser().resolve()
    return asyncio.run(
        _async_main(
            models=models,
            scenarios=scenarios,
            out=out,
            live=bool(args.live),
            timeout_secs=max(30, int(args.timeout_secs)),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
