#!/usr/bin/env bash
# Install repo git hooks (pre-push main CI gate).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="${ROOT}/.git/hooks"

if [[ ! -d "${HOOKS_DIR}" ]]; then
  echo "No .git/hooks — run from a git clone."
  exit 1
fi

chmod +x "${ROOT}/scripts/pre-push-main-gate.sh"

cat > "${HOOKS_DIR}/pre-push" <<'HOOK'
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
while read -r local_ref local_sha remote_ref remote_sha; do
  if [[ "${local_ref}" == "refs/heads/main" ]]; then
  "${ROOT}/scripts/pre-push-main-gate.sh" origin "" "${local_ref}"
  fi
done
HOOK

chmod +x "${HOOKS_DIR}/pre-push"
echo "Installed pre-push hook → scripts/pre-push-main-gate.sh (full ci-local.sh all on main push)."
