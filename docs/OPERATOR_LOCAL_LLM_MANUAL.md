# Operator manual — Local Sovereign LLM (Track M LOC12)

Run Queenswarm with **zero cloud LLM** using Ollama on your PC or server.

## Prerequisites

- Docker (recommended) or native [Ollama](https://ollama.com) on `127.0.0.1:11434`
- At least one model pulled, e.g. `ollama pull qwen2.5:7b`

## Quick start (Docker Compose)

```bash
docker compose -f docker-compose.yml -f docker-compose.local-llm.yml up -d ollama
docker exec -it queenswarm-ollama-1 ollama pull qwen2.5:7b
```

Add to `.env.prod`:

```env
LOCAL_LLM_ENABLED=true
OLLAMA_API_BASE=http://ollama:11434
OLLAMA_DEFAULT_MODEL=ollama/qwen2.5:7b
# Optional air-gap — blocks all cloud hops:
# LLM_AIRGAP=1
```

Redeploy, then in **Settings → LLM keys**:

1. Open **Local Inference · Sovereign LLM** → **Ping Ollama / vLLM** (expect green status).
2. In **Cost Guardian · LLM routing**, select **Local sovereign (Ollama only — $0)**.

## Verify

```bash
./scripts/operator-local-llm-preflight.sh
curl -s http://127.0.0.1:11434/api/tags | head
```

Start a solo session or workflow step — Prometheus metric `queenswarm_llm_local_inference_total` increments; cloud cost counters stay flat.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Ping failed | Check `OLLAMA_API_BASE`, firewall, model pull |
| Cloud model used | Set routing to `local_sovereign`; enable `LLM_AIRGAP=1` to hard-fail cloud |
| Empty model list | `ollama pull qwen2.5:7b` (or your `OLLAMA_DEFAULT_MODEL` tag) |

## vLLM (optional)

For OpenAI-compatible vLLM instead of Ollama:

```env
VLLM_API_BASE=http://127.0.0.1:8000
VLLM_DEFAULT_MODEL=openai/local-model
```

Ping uses `GET /v1/models`.

## Verified dataset export (LOC5)

After critic-approved sessions (closed review loop ≥4/5):

1. **Settings → LLM keys** → **Verified dataset export · Alpaca JSONL**
2. Preview sample rows → **Download JSONL**
3. Import into Unsloth Studio or Hugging Face for QLoRA fine-tune

CLI (requires operator JWT):

```bash
export OPERATOR_SMOKE_JWT="<dashboard-bearer>"
./scripts/operator-verified-dataset-export.sh ./my-tenant-dataset.jsonl
```

Only critic-approved deliverables and verified recipes are exported — secrets are redacted.
