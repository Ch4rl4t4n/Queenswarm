#!/usr/bin/env bash
set -euo pipefail

# Generates strong random placeholders for Compose / .env (stdout). Operators still must wire real LLM keys.

echo "# Generated $(date -u +%FT%TZ)"
echo "# --- Auth / Grafana ---"
echo "SECRET_KEY=$(openssl rand -hex 32)"
echo "GRAFANA_ADMIN_PASSWORD=$(openssl rand -hex 24)"
echo "DASHBOARD_JWT=$(openssl rand -hex 32)"
echo "NEO4J_PASSWORD=$(openssl rand -hex 16)"
echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)"
echo "# --- Optional machine token for POST /api/v1/auth/token ---"
echo "HIVE_TOKEN_CLIENT_ID=hive-runner"
echo "HIVE_TOKEN_CLIENT_SECRET=$(openssl rand -hex 32)"
