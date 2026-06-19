#!/usr/bin/env bash
# Print the single highest-priority operator action (read-only).
#
# Usage:
#   ./scripts/operator-next.sh
#   ./scripts/operator-next.sh --json
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export OPERATOR_NEXT_JSON=false
[[ "${1:-}" == "--json" ]] && export OPERATOR_NEXT_JSON=true

PENDING_JSON="$(./scripts/operator-pending-status.sh 2>/dev/null)"

PENDING_JSON="$PENDING_JSON" python3 <<'PY'
import json
import os

d = json.loads(os.environ["PENDING_JSON"])


def step(n, title, why, commands, doc=None):
    return {"priority": n, "title": title, "why": why, "commands": commands, "doc": doc}


hetzner = d.get("hetzner", {})
harness = d.get("harness", {})
solo = False
personal_os = False
try:
    import pathlib
    env_path = pathlib.Path(os.environ.get("ENV_FILE", ".env.prod"))
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith("SOLO_MODE_ENABLED="):
                solo = line.split("=", 1)[1].strip().lower() in ("1", "true", "yes", "on")
            if line.strip().startswith("PERSONAL_OS_MODE_ENABLED="):
                personal_os = line.split("=", 1)[1].strip().lower() in ("1", "true", "yes", "on")
except OSError:
    pass

if solo and personal_os and harness.get("webhook_ready"):
    out = step(
        1,
        "Personal OS daily operator stack",
        "Readiness green — mission-home, four-lanes, durable sessions. Run daily stack + evening loop.",
        [
            "./scripts/operator-personal-os-verify.sh",
            "./scripts/operator-evening-loop-smoke.sh",
            "./scripts/operator-life-os-smoke.sh",
            "./scripts/prod-session-walkthrough-gate.sh",
            "Mission Home → Daily plan → /agents#sessions → /ballroom → /foragers",
        ],
        "docs/SOLO_OPERATOR_MODE.md",
    )
elif solo and not harness.get("webhook_ready"):
    out = step(
        1,
        "Solo harness automation",
        "Queen Maintainer post-merge webhook + Forager daily cron.",
        [
            "./scripts/operator-solo-enable-modules.sh",
            "./scripts/operator-resolve-tenant-id.sh",
            "./scripts/operator-github-webhook-prep.sh",
            "./scripts/operator-harness-env-prep.sh",
            "ENV_FILE=.env.prod ./scripts/deploy-prod.sh",
        ],
        "docs/OPERATOR_HARNESS_WEBHOOK_SETUP.md",
    )
elif solo:
    vc_oauth_blocker = False
    vc_readiness = 100
    vc_simulate_complete = False
    audit: dict = {}
    try:
        import subprocess
        audit_raw = subprocess.run(
            ["./scripts/operator-virtual-company-readiness-audit.sh", "--json-only"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=".",
        )
        if audit_raw.returncode == 0 and audit_raw.stdout.strip():
            audit = json.loads(audit_raw.stdout)
            vc_readiness = int(audit.get("readiness_score") or 100)
            vc_oauth_blocker = not bool(audit.get("oauth_env_ready"))
            vc_simulate_complete = bool(
                audit.get("simulate_path_complete")
                or audit.get("checklist", {}).get("simulate_path_complete")
            )
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
        pass

    if vc_simulate_complete:
        publish = d.get("publish_lane", {})
        if not publish.get("social_publish_live_enabled"):
            out = step(
                1,
                "Publish lane — first live post",
                "Harness + VC simulate done. Complete Brain Pack → OAuth → Simulate → enable live.",
                [
                    "MERGE=1 ./scripts/operator-oauth-env-init.sh",
                    "./scripts/operator-social-oauth-prep-all.sh",
                    "./scripts/operator-social-oauth-status.sh",
                    "./scripts/operator-publish-lane-prep.sh",
                    "./scripts/operator-live-publish-prep.sh",
                    "./scripts/operator-live-publish-gate.sh",
                    "docs/OPERATOR_FIRST_LIVE_POST.md",
                    "Knowledge → Curated memory → Load starter pack (or ./scripts/operator-publish-lane-prep.sh)",
                    "Settings → AI harness → Publish onboarding checklist",
                    "docs/OPERATOR_META_INSTAGRAM_OAUTH.md",
                    "docs/OPERATOR_FIRST_LIVE_POST.md",
                    "# .env.prod: SOCIAL_PUBLISH_LIVE_ENABLED=true → ./scripts/deploy-prod.sh",
                ],
                "docs/OPERATOR_FIRST_LIVE_POST.md",
            )
        else:
            out = step(
                1,
                "Full app audit + UI walkthrough",
                f"Readiness {vc_readiness}% — simulate + swarms done. "
                "Prejdite aplikáciu krok za krokom.",
                [
                    "./scripts/operator-full-app-audit.sh",
                    "./scripts/operator-solo-status.sh",
                    "./scripts/operator-evening-loop-smoke.sh",
                    "reports/operator/full-app-walkthrough-*.md",
                ],
                "docs/AUTHENTICATED_PROD_WALKTHROUGH.md",
            )
    elif vc_oauth_blocker or vc_readiness < 100:
        connected = 0
        try:
            op = audit.get("oauth_progress") or audit.get("checklist", {}).get("oauth_progress") or {}
            connected = int(op.get("connected", 0))
        except (TypeError, ValueError):
            connected = 0
        if connected > 0 and vc_readiness < 100:
            why = (
                f"Readiness {vc_readiness}% — GitHub active. "
                "Add Notion internal token (~88%), then Gmail OAuth for 100%."
            )
            cmds = [
                "./scripts/operator-vc-notion-onboard.sh",
                "NOTION_INTEGRATION_TOKEN=secret_… APPLY=1 ./scripts/operator-vc-notion-onboard.sh",
                "./scripts/operator-oauth-register-guide.sh  # Gmail section",
                "./scripts/operator-post-oauth-verify.sh",
            ]
        else:
            why = (
                f"Readiness {vc_readiness}% — register OAuth apps or use manual tokens "
                "(gh auth → GitHub; Notion internal integration)."
            )
            cmds = [
                "./scripts/operator-oauth-one-shot.sh",
                "./scripts/operator-vc-manual-tokens.sh",
                "./scripts/operator-vc-notion-onboard.sh",
                "./scripts/operator-oauth-open-vendors.sh",
                "./scripts/operator-post-oauth-verify.sh",
            ]
        out = step(
            1,
            "Virtual Company OAuth + connectors",
            why,
            cmds,
            "docs/SOLO_OPERATOR_MODE.md",
        )
    else:
        out = step(
            2,
            "Solo post-launch ops",
            "Harness ready — ops crons, readiness audit, quarterly DR drill.",
            [
                "./scripts/operator-solo-readiness-audit.sh",
                "APPLY=1 ./scripts/install-ops-automation-cron.sh",
                "./scripts/dr-drill.sh",
            ],
            "docs/SOLO_OPERATOR_MODE.md",
        )
elif not hetzner.get("marked_sent"):
    out = step(
        2,
        "Hetzner abuse reply",
        "Infra risk — send prepared reply to abuse@hetzner.com.",
        [
            "./scripts/operator-hetzner-copy-email.sh",
            "# Send → abuse@hetzner.com · Subject: Re: AbuseID 11B0286:23",
            "./scripts/operator-mark-hetzner-sent.sh",
        ],
        "docs/OPERATOR_HETZNER_SEND.md",
    )
elif not harness.get("webhook_ready"):
    out = step(
        4,
        "Harness automation (optional)",
        "Queen Maintainer post-merge webhook + Forager daily cron.",
        [
            "./scripts/operator-resolve-tenant-id.sh",
            "./scripts/operator-github-webhook-prep.sh",
            "./scripts/operator-harness-env-prep.sh",
            "ENV_FILE=.env.prod ./scripts/deploy-prod.sh",
        ],
        "docs/OPERATOR_HARNESS_WEBHOOK_SETUP.md",
    )
else:
    out = step(
        5,
        "Launch complete — post-launch ops",
        "P0 done. Run handoff pack; schedule quarterly HA/DR drill.",
        [
            "./scripts/operator-handoff-pack.sh",
            "./scripts/operator-launch-gate.sh",
            "./scripts/dr-drill.sh",
        ],
        "docs/MISSION_EXECUTION_BACKLOG.md",
    )

if os.environ.get("OPERATOR_NEXT_JSON") == "true":
    print(json.dumps(out))
else:
    print("== Operator next action ==")
    print()
    print(f"Priority {out['priority']}: {out['title']}")
    print(out["why"])
    print()
    if out.get("doc"):
        print(f"Guide: {out['doc']}")
        print()
    print("Commands:")
    for cmd in out["commands"]:
        print(f"  {cmd}")
PY
