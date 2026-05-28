#!/usr/bin/env bash
# Validate production env file against Pydantic production_security_mode rules (no secrets printed).
#
# Usage: ENV_FILE=.env.prod ./scripts/validate-prod-env.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/.env.prod}"
SINGLE_ADMIN_REQUIRED="${SINGLE_ADMIN_REQUIRED:-0}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "validate-prod-env: missing ${ENV_FILE}" >&2
  exit 1
fi

echo "validate-prod-env: checking ${ENV_FILE}"

docker compose -p queenswarm_prod -f "${ROOT}/docker-compose.base.yml" -f "${ROOT}/docker-compose.prod.yml" \
  --env-file "$ENV_FILE" run --rm --no-deps \
  -e "SINGLE_ADMIN_REQUIRED=${SINGLE_ADMIN_REQUIRED}" \
  backend python - <<'PY'
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
solo_mode_enabled = bool(getattr(s, "solo_mode_enabled", False))
single_admin_mode = bool(getattr(s, "single_admin_mode", False))
print(f"  solo_mode_enabled={solo_mode_enabled}")
print(f"  single_admin_mode={single_admin_mode}")

if single_admin_mode and not solo_mode_enabled:
    print(
        "  ERROR: SINGLE_ADMIN_MODE=true requires SOLO_MODE_ENABLED=true.",
        file=sys.stderr,
    )
    sys.exit(1)

single_admin_required = os.getenv("SINGLE_ADMIN_REQUIRED", "0").strip() == "1"
if single_admin_required and not single_admin_mode:
    print("  ERROR: SINGLE_ADMIN_REQUIRED=1 but SINGLE_ADMIN_MODE=false.", file=sys.stderr)
    sys.exit(1)
PY
