#!/usr/bin/env python3
"""Print Queenswarm executor SMTP readiness (never prints secrets).

Run on the backend container, e.g. ``docker compose exec backend python3 /app/scripts/check_notification_env.py``.
Grafana alerting email uses separate ``GF_SMTP_*`` variables (see ``.env.example``).
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    smtp_host = (os.getenv("SMTP_HOST") or "").strip()
    smtp_port = (os.getenv("SMTP_PORT") or "").strip()
    smtp_user = (os.getenv("SMTP_USER") or "").strip()
    smtp_pass = (os.getenv("SMTP_PASS") or "").strip()

    ok_user = bool(smtp_user)
    ok_pass = bool(smtp_pass)
    print(f"SMTP host: {'configured — ' + smtp_host if smtp_host else 'not set (default smtp.gmail.com in executor if user set)'}")
    print(f"SMTP port: {smtp_port or '587 (executor default when unset)'}")
    print(f"SMTP user (agent email): {'configured' if ok_user else 'not set — add SMTP_USER to .env'}")
    print(f"SMTP password: {'configured' if ok_pass else 'not set — add SMTP_PASS to .env'}")
    if ok_user and not ok_pass:
        print("\n⚠ SMTP_USER is set but SMTP_PASS missing — SMTP login will skip in executor.")

    gf = (os.getenv("GF_SMTP_ENABLED") or "").strip().lower() in {"1", "true", "yes"}
    if gf:
        print("GF_SMTP_ENABLED=true on this process — Grafana container env (not necessarily here on API).")
    else:
        print("Grafana uses GF_SMTP_* on the grafana service; see root .env.example.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
