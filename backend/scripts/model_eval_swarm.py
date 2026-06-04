#!/usr/bin/env python3
"""Generate a simulate-first model evaluation plan for Queenswarm LLM routing."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODELS = [
    "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
    "xai/grok-3-mini",
    "anthropic/claude-haiku-4-5-20251001",
    "openai/gpt-4o-mini",
]
DEFAULT_OUTPUT = Path("exports/model-evals/MODEL_EVAL_REPORT.md")


@dataclass(frozen=True)
class EvalScenario:
    """One model-router evaluation scenario."""

    name: str
    prompt: str
    success_criteria: list[str]

    def __repr__(self) -> str:
        return f"EvalScenario(name={self.name!r}, criteria={len(self.success_criteria)})"


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


def render_eval_plan_report(models: list[str], scenarios: list[EvalScenario]) -> str:
    """Render a markdown evaluation plan that is safe before API keys exist."""

    lines = [
        "# Model Evaluation Swarm",
        "",
        "Purpose: compare candidate LLMs for Queenswarm orchestration before adding them to default routing.",
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
            "## Next Implementation Step",
            "",
            "Wire live runs through `LiteLLMRouter.complete_single_model` once `OPENROUTER_API_KEY` is configured.",
        ],
    )
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", action="append", dest="models", help="Candidate LiteLLM model slug.")
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT), help="Markdown report output path.")
    args = parser.parse_args(argv)

    models = args.models or DEFAULT_MODELS
    report = render_eval_plan_report(models=models, scenarios=default_scenarios())
    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(report.rstrip())
    print(f"\nout={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
