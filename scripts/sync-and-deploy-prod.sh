#!/usr/bin/env bash
# Sync this repository to the VPS and rebuild Compose stack (expects SSH key auth).
# Prereq: scripts/provision-remote-ssh-key.sh (or authorized_keys manually).
#
# Usage:
#   ./scripts/sync-and-deploy-prod.sh
#
# Override:
#   QUEENSWARM_SSH_HOST=... QUEENSWARM_REMOTE_DIR=/opt/queenswarm ./scripts/sync-and-deploy-prod.sh
set -euo pipefail

HOST="${QUEENSWARM_SSH_HOST:-46.224.120.151}"
SSH_USER="${QUEENSWARM_SSH_USER:-root}"
KEY="${QUEENSWARM_SSH_PRIVATE_KEY:-$HOME/.ssh/queenswarm_prod_ed25519}"
REMOTE_DIR="${QUEENSWARM_REMOTE_DIR:-/opt/queenswarm}"

if [[ ! -f "$KEY" ]]; then
  echo "Missing private key $KEY" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RSYNC_SSH="ssh -i ${KEY} -o StrictHostKeyChecking=no"

rsync -az --delete \
  -e "${RSYNC_SSH}" \
  --filter='P .env' \
  --filter='P .env.*' \
  --exclude '.git/' \
  --exclude 'backend/.venv/' \
  --exclude 'frontend/node_modules/' \
  --exclude 'frontend/.next/' \
  --exclude '**/__pycache__/' \
  --exclude '.cursor/' \
  --exclude '*.pyc' \
  "${REPO_ROOT}/" \
  "${SSH_USER}@${HOST}:${REMOTE_DIR}/"

ssh -i "$KEY" -o StrictHostKeyChecking=no "${SSH_USER}@${HOST}" \
  "mkdir -p ${REMOTE_DIR} && cd ${REMOTE_DIR} && docker compose up -d --build"

echo "Deploy issued. Smoke: curl -sI https://queenswarm.love | head -5"
