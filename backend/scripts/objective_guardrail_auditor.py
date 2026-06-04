#!/usr/bin/env python3
"""Audit agent objectives for unsafe live-action and revenue optimization patterns."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_OUTPUT = Path("exports/guardrail-audits/OBJECTIVE_GUARDRAIL_AUDIT.md")


@dataclass(frozen=True)
class AuditObjective:
    """One agent, skill, or simulation objective to audit."""

    name: str
    objective: str
    guardrails: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"AuditObjective(name={self.name!r}, guardrails={len(self.guardrails)})"


@dataclass(frozen=True)
class ObjectiveAudit:
    """Audit result for one objective."""

    name: str
    verdict: str
    risks: list[str]
    safe_rewrite: str

    def __repr__(self) -> str:
        return f"ObjectiveAudit(name={self.name!r}, verdict={self.verdict!r})"


def _contains_any(haystack: str, needles: tuple[str, ...]) -> bool:
    """Return True when any phrase appears in lowercased text."""

    return any(needle in haystack for needle in needles)


def _safe_rewrite(objective: AuditObjective) -> str:
    """Return a safer advisory objective rewrite."""

    return (
        f"Advise on '{objective.name}' through simulation only. "
        "No live actions are permitted without explicit operator approval, audit logging, "
        "and a review of customer trust, compliance, and long-term value."
    )


def audit_objective(objective: AuditObjective) -> ObjectiveAudit:
    """Audit one objective and return a conservative verdict."""

    text = " ".join([objective.objective, *objective.guardrails]).lower()
    objective_only = objective.objective.lower()
    guardrails = " ".join(objective.guardrails).lower()
    risks: list[str] = []

    if _contains_any(
        objective_only,
        ("change prices live", "changing prices live", "live price", "publish live", "execute live", "send outreach"),
    ):
        risks.append("live_action_without_approval")
    if _contains_any(objective_only, ("autonomous pricing", "dynamic pricing", "change prices", "pricing bot")):
        risks.append("autopricing_without_approval")
    if _contains_any(objective_only, ("maximize profit", "above competitor", "competitor average", "raise prices until")):
        risks.append("supracompetitive_pricing_pattern")
    if _contains_any(objective_only, ("spam", "mass dm", "scrape emails", "cold email everyone")):
        risks.append("spam_or_manipulative_growth")
    if "approval" not in guardrails and _contains_any(text, ("price", "publish", "send", "execute", "launch")):
        risks.append("missing_approval_gate")
    if "customer trust" not in guardrails and _contains_any(objective_only, ("maximize profit", "growth hack", "conversion at all costs")):
        risks.append("missing_customer_trust_constraint")

    if any(risk in risks for risk in ("live_action_without_approval", "autopricing_without_approval", "spam_or_manipulative_growth")):
        verdict = "blocked"
    elif risks:
        verdict = "review"
    else:
        verdict = "review"

    return ObjectiveAudit(
        name=objective.name,
        verdict=verdict,
        risks=risks or ["none_detected"],
        safe_rewrite=_safe_rewrite(objective),
    )


def render_audit_report(audits: list[ObjectiveAudit]) -> str:
    """Render a file-based objective audit report."""

    lines = [
        "# Objective Guardrail Audit",
        "",
        "Purpose: catch unsafe agent objectives before Queenswarm runs simulations, tools, or live actions.",
        "",
        "## Global Rule",
        "",
        "No live actions are permitted without explicit operator approval and audit logging.",
        "",
        "## Audits",
        "",
    ]
    for audit in audits:
        lines.extend(
            [
                f"### {audit.name}",
                "",
                f"- verdict: {audit.verdict}",
                "- risks:",
            ],
        )
        for risk in audit.risks:
            lines.append(f"  - {risk}")
        lines.extend(
            [
                "",
                "Safe objective rewrite:",
                "",
                audit.safe_rewrite,
                "",
            ],
        )
    return "\n".join(lines).rstrip() + "\n"


def _slug(value: str) -> str:
    """Return a stable filename slug."""

    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "objective-audit"


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="gumroad launch advisor")
    parser.add_argument(
        "--objective",
        default="recommend a sustainable Gumroad launch price after simulation",
    )
    parser.add_argument(
        "--guardrail",
        action="append",
        dest="guardrails",
        default=[],
        help="Guardrail phrase; can be repeated.",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    objective = AuditObjective(
        name=str(args.name),
        objective=str(args.objective),
        guardrails=list(args.guardrails or []),
    )
    report = render_audit_report([audit_objective(objective)])
    output = Path(args.out).expanduser().resolve()
    if output.name == DEFAULT_OUTPUT.name and str(args.out) == str(DEFAULT_OUTPUT):
        output = output.parent / f"{_slug(objective.name)}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(report.rstrip())
    print(f"\nout={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
