#!/usr/bin/env bash
# Track M LOC9 — Host fine-tune runner (Unsloth/QLoRA). Invoked only when LOCAL_FINETUNE_EXECUTE=1.
#
# Usage:
#   ./scripts/operator-local-finetune-run.sh --dataset ./data.jsonl --base qwen2.5:7b --name my-adapter --epochs 1
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DATASET=""
BASE=""
NAME=""
EPOCHS="1"

usage() {
  cat <<'EOF'
operator-local-finetune-run.sh — GPU host fine-tune (LOC9)

  --dataset PATH   Alpaca JSONL dataset (required)
  --base MODEL     Base model name (required)
  --name TAG       Output adapter Ollama tag (required)
  --epochs N       Training epochs (default 1)
  --help           Show help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dataset) DATASET="${2:-}"; shift 2 ;;
    --base) BASE="${2:-}"; shift 2 ;;
    --name) NAME="${2:-}"; shift 2 ;;
    --epochs) EPOCHS="${2:-}"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "${DATASET}" || -z "${BASE}" || -z "${NAME}" ]]; then
  echo "Missing --dataset, --base, or --name" >&2
  usage
  exit 2
fi

if [[ ! -f "${DATASET}" ]]; then
  echo "Dataset not found: ${DATASET}" >&2
  exit 1
fi

ROW_COUNT="$(grep -c '{' "${DATASET}" || true)"
if [[ "${ROW_COUNT}" -lt 1 ]]; then
  echo "Dataset has no JSONL rows: ${DATASET}" >&2
  exit 1
fi

echo "[loc9] fine-tune validated: dataset=${DATASET} rows=${ROW_COUNT} base=${BASE} name=${NAME} epochs=${EPOCHS}"
echo "[loc9] Replace this stub with Unsloth CLI on GPU host when ready."
echo "[loc9] Next: ./scripts/operator-unsloth-bridge.sh --gguf ./exports/${NAME}.gguf --name ${NAME} --register"
exit 0
