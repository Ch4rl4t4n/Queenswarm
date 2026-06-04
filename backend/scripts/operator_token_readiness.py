#!/usr/bin/env python3
"""Summarize optional operator token readiness without exposing secret values."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TOKENS_FILE = ROOT / ".env.prod.tokens"
DEFAULT_OUTPUT = ROOT / "exports" / "OPERATOR_TOKEN_READINESS.md"


@dataclass(frozen=True)
class TokenStatus:
    """Masked readiness state for one optional operator token."""

    key: str
    label: str
    configured: bool
    purpose: str

    def __repr__(self) -> str:
        return f"TokenStatus(key={self.key!r}, configured={self.configured})"


TOKEN_SPECS: tuple[tuple[str, str, str], ...] = (
    ("OPENROUTER_API_KEY", "OpenRouter / Nemotron", "Run Nemotron model evals via OpenRouter."),
    ("SKILL_FACTORY_GUMROAD_ACCESS_TOKEN", "Gumroad API token", "Create Gumroad draft products via API."),
    ("SKILL_FACTORY_GUMROAD_LISTING_ENABLED", "Gumroad listing gate", "Enable draft listing flow after token exists."),
    ("GITHUB_PAT", "GitHub PAT", "Create teaser repositories and R&D lane artifacts."),
    ("SMTP_PASS", "SMTP app password", "Send operator email alerts and digests."),
    ("NOTIFY_EMAIL", "Notify email", "Receive operator alerts and audit rollups."),
)


def _load_env_file(path: Path) -> dict[str, str]:
    """Load simple KEY=VALUE pairs from a dotenv-style file."""

    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _looks_configured(value: str | None) -> bool:
    """Return False for empty, obvious placeholder, or change-me values."""

    if value is None:
        return False
    cleaned = value.strip()
    if not cleaned:
        return False
    lowered = cleaned.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    placeholder_bits = ("your-", "your_", "change-me", "changeme", "placeholder", "example", "todo")
    return not any(bit in lowered for bit in placeholder_bits)


def collect_token_statuses(tokens_file: Path = DEFAULT_TOKENS_FILE) -> list[TokenStatus]:
    """Collect token readiness from a dotenv file without returning raw secrets."""

    values = _load_env_file(tokens_file)
    return [
        TokenStatus(
            key=key,
            label=label,
            configured=_looks_configured(values.get(key)),
            purpose=purpose,
        )
        for key, label, purpose in TOKEN_SPECS
    ]


def render_token_readiness(statuses: list[TokenStatus]) -> str:
    """Render token readiness markdown."""

    missing = [status for status in statuses if not status.configured]
    lines = [
        "# Operator Token Readiness",
        "",
        "This report only shows configured/missing state. It never prints token values.",
        "",
        "## Tokens",
        "",
    ]
    for status in statuses:
        state = "configured" if status.configured else "missing"
        lines.append(f"- `{status.key}` — {state} ({status.label}): {status.purpose}")
    lines.extend(
        [
            "",
            "## Next Action",
            "",
        ],
    )
    if missing:
        lines.append("Add missing tokens to `.env.prod.tokens` or Settings → AI / Integrations, then rerun this report.")
    else:
        lines.append("All optional operator tokens in this checklist are configured.")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokens-file", default=str(DEFAULT_TOKENS_FILE))
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    statuses = collect_token_statuses(Path(args.tokens_file).expanduser().resolve())
    report = render_token_readiness(statuses)
    output = Path(args.out).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(report.rstrip())
    print(f"\nout={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
