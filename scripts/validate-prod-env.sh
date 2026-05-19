#!/usr/bin/env bash
# Validate production env file against Pydantic production_security_mode rules (no secrets printed).
#
# Usage: ENV_FILE=.env.prod ./scripts/validate-prod-env.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/.env.prod}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "validate-prod-env: missing ${ENV_FILE}" >&2
  exit 1
fi

echo "validate-prod-env: checking ${ENV_FILE}"

docker compose -p queenswarm_prod -f "${ROOT}/docker-compose.base.yml" -f "${ROOT}/docker-compose.prod.yml" \
  --env-file "$ENV_FILE" run --rm --no-deps backend python - <<'PY'
from __future__ import annotations

import os
import sys

from pydantic import ValidationError

# Compose injects env; re-load settings fresh inside container.
from app.core.config import Settings

try:
    Settings()
except ValidationError as exc:
    print("validate-prod-env: FAILED — settings validation error:", file=sys.stderr)
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", ()))
        print(f"  {loc}: {err.get('msg')}", file=sys.stderr)
    sys.exit(1)

s = Settings()
print("validate-prod-env: OK")
print(f"  production_security_mode={s.production_security_mode}")
print(f"  access_token_expire_minutes={s.access_token_expire_minutes}")
print(f"  refresh_token_expire_days={s.refresh_token_expire_days}")
print(f"  enable_2fa={s.enable_2fa}")
print(f"  security_2fa_advanced_enabled={s.security_2fa_advanced_enabled}")
print(f"  rate_limit_enabled={s.rate_limit_enabled}")
print(f"  connector_vault_configured={bool((s.connector_vault_fernet_key or '').strip())}")

if s.skill_export_premium_enabled and not (s.stripe_secret_key or "").strip():
    print("  WARN: SKILL_EXPORT_PREMIUM_ENABLED=true but STRIPE_SECRET_KEY is empty", file=sys.stderr)
if s.skill_export_premium_enabled and not (s.stripe_webhook_secret or "").strip():
    print("  WARN: SKILL_EXPORT_PREMIUM_ENABLED=true but STRIPE_WEBHOOK_SECRET is empty", file=sys.stderr)
PY
