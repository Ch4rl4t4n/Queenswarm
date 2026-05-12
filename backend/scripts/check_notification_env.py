#!/usr/bin/env python3
"""Print Slack + SMTP env presence (no secret values). Operators run via ``docker exec backend``."""

from __future__ import annotations

import os
import sys


def main() -> None:
    slack = (os.getenv("SLACK_WEBHOOK_URL") or "").strip()
    smtp_user = (os.getenv("SMTP_USER") or "").strip()
    smtp_pass = (os.getenv("SMTP_PASS") or "").strip()
    print(f"Slack webhook: {'configured' if slack else 'not set — add SLACK_WEBHOOK_URL to .env'}")
    print(f"Email SMTP user: {'configured' if smtp_user else 'not set — add SMTP_USER to .env'}")
    print(f"Email SMTP password: {'configured' if smtp_pass else 'not set — add SMTP_PASS to .env'}")
    if not slack and not smtp_user:
        print(
            "\nOptional: set SLACK_WEBHOOK_URL for incoming webhooks, "
            "or SMTP_USER/SMTP_PASS/SMTP_HOST/SMTP_PORT for agent email delivery.",
        )


if __name__ == "__main__":
    sys.exit(main())
