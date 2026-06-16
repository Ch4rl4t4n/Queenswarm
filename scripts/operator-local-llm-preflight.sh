#!/usr/bin/env bash
# Track M LOC10 — Local LLM hardware preflight (Ollama ping + RAM/disk guidance).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }
warn() { echo "  WARN $*"; }

OLLAMA_BASE="${OLLAMA_API_BASE:-http://127.0.0.1:11434}"
DEFAULT_MODEL="${OLLAMA_DEFAULT_MODEL:-ollama/qwen2.5:7b}"
MODEL_TAG="${DEFAULT_MODEL#ollama/}"

echo "=== Local LLM preflight (LOC10) ==="
echo "Ollama base: ${OLLAMA_BASE}"
echo "Default model: ${DEFAULT_MODEL}"

if [[ -r /proc/meminfo ]]; then
  mem_kb="$(awk '/MemTotal:/ {print $2}' /proc/meminfo)"
  mem_gb=$((mem_kb / 1024 / 1024))
  echo "RAM: ~${mem_gb} GiB total"
  if [[ "${mem_gb}" -lt 16 ]]; then
    warn "≤16 GiB — prefer 7B Q4 models (e.g. qwen2.5:7b)"
  elif [[ "${mem_gb}" -lt 48 ]]; then
    pass "RAM suitable for 7B–14B local inference"
  else
    pass "RAM suitable for larger local models / QLoRA"
  fi
else
  warn "Cannot read /proc/meminfo — skip RAM check"
fi

df_out="$(df -h "${ROOT}" 2>/dev/null | tail -1 || true)"
if [[ -n "${df_out}" ]]; then
  echo "Disk (${ROOT}): ${df_out}"
  pass "Disk probe"
else
  warn "Disk probe skipped"
fi

if command -v curl >/dev/null 2>&1; then
  if curl -sf --max-time 5 "${OLLAMA_BASE}/api/tags" >/dev/null; then
    pass "Ollama reachable at ${OLLAMA_BASE}"
    if curl -sf --max-time 5 "${OLLAMA_BASE}/api/tags" | grep -q "${MODEL_TAG%%:*}"; then
      pass "Model tag present (${MODEL_TAG})"
    else
      warn "Model ${MODEL_TAG} not in tags — run: ollama pull ${MODEL_TAG}"
    fi
  else
    fail "Ollama not reachable — start: docker compose -f docker-compose.yml -f docker-compose.local-llm.yml up -d ollama"
  fi
else
  warn "curl missing — skip Ollama ping"
fi

echo ""
echo "Recommended next steps:"
echo "  1. Settings → LLM keys → Local Inference → Ping"
echo "  2. Cost Guardian routing → local_sovereign"
echo "  3. Analytics workspace → dispatch with LOC13 local bees"
echo ""

if [[ "$FAIL" -eq 0 ]]; then
  echo "LOCAL LLM PREFLIGHT: PASS"
  exit 0
fi
echo "LOCAL LLM PREFLIGHT: FAIL ($FAIL)"
exit 1
