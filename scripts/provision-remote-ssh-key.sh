#!/usr/bin/env bash
# One-time: install ~/.ssh/queenswarm_prod_ed25519.pub into root's authorized_keys on the VPS.
# Usage (from any machine that has sshpass):
#   export QUEENSWARM_ROOT_PASSWORD='your-root-password'
#   ./scripts/provision-remote-ssh-key.sh
set -euo pipefail

HOST="${QUEENSWARM_SSH_HOST:-46.224.120.151}"
USER="${QUEENSWARM_SSH_USER:-root}"
KEY="${QUEENSWARM_SSH_PRIVATE_KEY:-$HOME/.ssh/queenswarm_prod_ed25519}"
PUB="${KEY}.pub"

if [[ ! -f "$PUB" ]]; then
  echo "Missing $PUB — generate with: ssh-keygen -t ed25519 -f ${KEY%.pub} -N '' -C queenswarm-deploy" >&2
  exit 1
fi

if [[ -z "${QUEENSWARM_ROOT_PASSWORD:-}" ]]; then
  echo "Set QUEENSWARM_ROOT_PASSWORD to the server's root password (one time), then re-run." >&2
  exit 1
fi

if ! command -v sshpass >/dev/null 2>&1; then
  echo "Install sshpass (e.g. apt-get install -y sshpass)." >&2
  exit 1
fi

export SSHPASS="${QUEENSWARM_ROOT_PASSWORD}"
sshpass -e ssh-copy-id -f -o StrictHostKeyChecking=accept-new -i "$PUB" "${USER}@${HOST}"
unset SSHPASS
unset QUEENSWARM_ROOT_PASSWORD

echo "OK — tested with: ssh -i ${KEY} ${USER}@${HOST} hostname"
