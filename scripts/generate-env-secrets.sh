#!/usr/bin/env bash
set -euo pipefail

# Generates strong random placeholders for Compose / .env (stdout). Operators still must wire real LLM keys.

PYTHON_BIN="$(command -v python3 || true)"
FERNET_KEY=""
if [[ -n "${PYTHON_BIN}" ]]; then
  FERNET_KEY="$("${PYTHON_BIN}" -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || true)"
fi
if [[ -z "${FERNET_KEY}" ]]; then
  FERNET_KEY="replace-with-python-cryptography-fernet-Fernet-generate-key"
fi

echo "# Generated $(date -u +%FT%TZ)"
echo "# --- Auth / Grafana (64-byte hex SECRET_KEY satisfies PRODUCTION_SECURITY_MODE) ---"
echo "SECRET_KEY=$(openssl rand -hex 32)"
echo "CONNECTOR_VAULT_FERNET_KEY=${FERNET_KEY}"
echo "GRAFANA_ADMIN_PASSWORD=$(openssl rand -hex 24)"
echo "DASHBOARD_JWT=$(openssl rand -hex 32)"
echo "NEO4J_PASSWORD=$(openssl rand -hex 16)"
echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)"
echo "REDIS_PASSWORD=$(openssl rand -hex 32)"
echo "# --- Production hardening (align with backend config validators) ---"
echo "PRODUCTION_SECURITY_MODE=true"
echo "ACCESS_TOKEN_EXPIRE_MINUTES=15"
echo "REFRESH_TOKEN_EXPIRE_DAYS=7"
echo "RATE_LIMIT_ENABLED=true"
echo "ENABLE_2FA=true"
echo "SECURITY_2FA_ADVANCED_ENABLED=true"
echo "API_KEY_MANAGEMENT_ENABLED=true"
echo "# --- Optional machine token for POST /api/v1/auth/token ---"
echo "HIVE_TOKEN_CLIENT_ID=hive-runner"
echo "HIVE_TOKEN_CLIENT_SECRET=$(openssl rand -hex 32)"
