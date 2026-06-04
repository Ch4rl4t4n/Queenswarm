#!/usr/bin/env python3
"""Aggregate first-revenue operator reports into one status runbook."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

EXPORT_ROOT = Path(__file__).resolve().parents[2] / "exports"
DEFAULT_OUTPUT = EXPORT_ROOT / "OPERATOR_REVENUE_STATUS.md"


@dataclass(frozen=True)
class RevenueStatusInputs:
    """File inputs for the revenue operator status report."""

    upload_queue: Path
    scorecard: Path
    business_simulation: Path
    objective_audit: Path
    model_eval: Path

    def __repr__(self) -> str:
        return f"RevenueStatusInputs(upload_queue={self.upload_queue!s})"


def _read(path: Path) -> str:
    """Read text if the report exists."""

    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _first_match(text: str, pattern: str, default: str = "missing") -> str:
    """Return the first regex match group or a default."""

    match = re.search(pattern, text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return default


def _first_product(upload_queue_md: str) -> str:
    """Return first product row from the upload queue."""

    return _first_match(upload_queue_md, r"^1\.\s+(`[^`]+`.*)$")


def _business_recommendation(simulation_md: str) -> str:
    """Return the first recommendation sentence."""

    for line in simulation_md.splitlines():
        clean = line.strip()
        if clean.startswith("Start with "):
            return clean
    return "missing"


def _model_eval_hint(model_eval_md: str) -> str:
    """Return model eval state with Nemotron mention when present."""

    if "nemotron" in model_eval_md.lower():
        return "Nemotron candidate queued for OpenRouter eval."
    if model_eval_md:
        return "Model eval report available."
    return "missing"


def render_revenue_status(inputs: RevenueStatusInputs) -> str:
    """Render a single operator runbook from revenue reports."""

    upload_queue_md = _read(inputs.upload_queue)
    scorecard_md = _read(inputs.scorecard)
    simulation_md = _read(inputs.business_simulation)
    audit_md = _read(inputs.objective_audit)
    model_eval_md = _read(inputs.model_eval)

    readiness = _first_match(scorecard_md, r"^(Ready:\s+\*\*[^*]+\*\*)$")
    first_product = _first_product(upload_queue_md)
    audit_verdict = _first_match(audit_md, r"^-\s+(verdict:\s+\w+)$")
    business_recommendation = _business_recommendation(simulation_md)
    model_eval_hint = _model_eval_hint(model_eval_md)
    missing = [
        label
        for label, body in (
            ("upload_queue", upload_queue_md),
            ("scorecard", scorecard_md),
            ("business_simulation", simulation_md),
            ("objective_audit", audit_md),
            ("model_eval", model_eval_md),
        )
        if not body
    ]
    next_action = "Upload product #1 from `exports/gumroad-ready/UPLOAD_QUEUE.md`."
    if missing:
        next_action = "Regenerate operator reports before upload."

    lines = [
        "# Queenswarm Revenue Operator Status",
        "",
        "Single source of truth for the first Gumroad revenue loop.",
        "",
        "## Current State",
        "",
        f"- Product readiness: {readiness}",
        f"- First upload candidate: {first_product}",
        f"- Objective audit: {audit_verdict}",
        f"- Strategy simulation: {business_recommendation}",
        f"- Model eval: {model_eval_hint}",
        "",
        "## Missing Reports",
        "",
    ]
    if missing:
        for item in missing:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Next Operator Action",
            "",
            next_action,
            "",
            "## Source Files",
            "",
            f"- `{inputs.upload_queue}`",
            f"- `{inputs.scorecard}`",
            f"- `{inputs.business_simulation}`",
            f"- `{inputs.objective_audit}`",
            f"- `{inputs.model_eval}`",
        ],
    )
    return "\n".join(lines).rstrip() + "\n"


def default_inputs(export_root: Path = EXPORT_ROOT) -> RevenueStatusInputs:
    """Return default report locations."""

    return RevenueStatusInputs(
        upload_queue=export_root / "gumroad-ready" / "UPLOAD_QUEUE.md",
        scorecard=export_root / "GUMROAD_SCORECARD.md",
        business_simulation=export_root / "business-simulations" / "GUMROAD_LAUNCH_STRATEGY.md",
        objective_audit=export_root / "guardrail-audits" / "GUMROAD_OBJECTIVE_AUDIT.md",
        model_eval=export_root / "model-evals" / "MODEL_EVAL_REPORT.md",
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", default=str(EXPORT_ROOT))
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    export_root = Path(args.export_root).expanduser().resolve()
    report = render_revenue_status(default_inputs(export_root))
    output = Path(args.out).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(report.rstrip())
    print(f"\nout={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
