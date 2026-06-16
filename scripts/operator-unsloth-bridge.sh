#!/usr/bin/env bash
# Track M LOC7 — Import Unsloth GGUF/LoRA export into Ollama + optional Queenswarm registry.
#
# Usage:
#   ./scripts/operator-unsloth-bridge.sh --gguf ./model.gguf --name queenswarm-tenant-v1
#   ./scripts/operator-unsloth-bridge.sh --gguf ./adapter.gguf --name my-lora --base qwen2.5:7b --register
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

GGUF_PATH=""
NAME=""
BASE_MODEL=""
SYSTEM_PROMPT=""
DRY_RUN=0
REGISTER=0
API_BASE="${QUEENSWARM_BASE_URL:-https://queenswarm.love}"
JWT="${OPERATOR_SMOKE_JWT:-}"

usage() {
  cat <<'EOF'
operator-unsloth-bridge.sh — Unsloth → Ollama import (LOC7)

  --gguf PATH        Path to GGUF or merged adapter file (required)
  --name TAG         Ollama model tag (required)
  --base MODEL       Base model tag when importing LoRA adapter
  --system TEXT      Optional SYSTEM prompt in Modelfile
  --dry-run          Print Modelfile + commands only
  --register         POST adapter to Queenswarm registry (needs OPERATOR_SMOKE_JWT)
  --help             Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --gguf) GGUF_PATH="${2:-}"; shift 2 ;;
    --name) NAME="${2:-}"; shift 2 ;;
    --base) BASE_MODEL="${2:-}"; shift 2 ;;
    --system) SYSTEM_PROMPT="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --register) REGISTER=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "${GGUF_PATH}" || -z "${NAME}" ]]; then
  echo "Missing --gguf and/or --name" >&2
  usage
  exit 2
fi

if [[ ! -f "${GGUF_PATH}" ]]; then
  echo "GGUF file not found: ${GGUF_PATH}" >&2
  exit 1
fi

PYTHON="${ROOT}/backend/venv/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
  PYTHON="$(command -v python3 || true)"
fi
if [[ -z "${PYTHON}" ]]; then
  echo "python3 required for Modelfile generation" >&2
  exit 1
fi

export PYTHONPATH="${ROOT}/backend${PYTHONPATH:+:${PYTHONPATH}}"
PLAN="$(
  UNSLOTH_GGUF="${GGUF_PATH}" \
  UNSLOTH_NAME="${NAME}" \
  UNSLOTH_BASE="${BASE_MODEL}" \
  UNSLOTH_SYSTEM="${SYSTEM_PROMPT}" \
  "${PYTHON}" - <<'PY'
import json
import os

from app.application.services.unsloth_bridge_service import (
    UnslothBridgeValidateIn,
    build_unsloth_bridge_plan,
)

payload = UnslothBridgeValidateIn(
    name=os.environ["UNSLOTH_NAME"],
    gguf_path=os.environ["UNSLOTH_GGUF"],
    base_model=os.environ.get("UNSLOTH_BASE", ""),
    system_prompt=os.environ.get("UNSLOTH_SYSTEM", ""),
)
print(json.dumps(build_unsloth_bridge_plan(payload).model_dump(mode="json")))
PY
)"

TAG="$(echo "${PLAN}" | "${PYTHON}" -c 'import json,sys; print(json.load(sys.stdin)["ollama_tag"])')"
SLUG="$(echo "${PLAN}" | "${PYTHON}" -c 'import json,sys; print(json.load(sys.stdin)["litellm_slug"])')"
MODELFILE_BODY="$(echo "${PLAN}" | "${PYTHON}" -c 'import json,sys; print(json.load(sys.stdin)["modelfile_body"], end="")')"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TMPDIR}"' EXIT
MODELFILE="${TMPDIR}/Modelfile"
printf '%s' "${MODELFILE_BODY}" > "${MODELFILE}"

echo "=== Unsloth bridge (LOC7) ==="
echo "Ollama tag: ${TAG}"
echo "LiteLLM slug: ${SLUG}"
echo "Modelfile: ${MODELFILE}"
echo ""
cat "${MODELFILE}"
echo ""

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "DRY RUN — would run: ollama create \"${TAG}\" -f \"${MODELFILE}\""
else
  if ! command -v ollama >/dev/null 2>&1; then
    echo "ollama CLI not found — install Ollama or use Docker exec" >&2
    exit 1
  fi
  ollama create "${TAG}" -f "${MODELFILE}"
  echo "OK — ollama create ${TAG}"
fi

if [[ "${REGISTER}" -eq 1 ]]; then
  if [[ -z "${JWT}" ]]; then
    echo "OPERATOR_SMOKE_JWT required for --register" >&2
    exit 1
  fi
  if ! command -v jq >/dev/null 2>&1; then
    echo "jq required for --register" >&2
    exit 1
  fi
  curl -fsSL -X POST "${API_BASE}/api/v1/llm-routing/local-adapters" \
    -H "Authorization: Bearer ${JWT}" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
      --arg name "${TAG}" \
      --arg tag "${TAG}" \
      --arg path "${GGUF_PATH}" \
      '{name: $name, ollama_tag: $tag, kind: "gguf", source_path: $path, activate: true}')" \
    >/dev/null
  echo "OK — registered adapter in Queenswarm registry (active)"
fi

echo "Next: Settings → LLM keys → Local adapters · routing local_sovereign → ${SLUG}"
