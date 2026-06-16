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

## Unsloth bridge (LOC7)

After fine-tuning in Unsloth Studio (external GPU):

```bash
./scripts/operator-unsloth-bridge.sh --gguf ./exports/model.gguf --name queenswarm-v1 --dry-run
./scripts/operator-unsloth-bridge.sh --gguf ./exports/model.gguf --name queenswarm-v1 --register
```

`--register` requires `OPERATOR_SMOKE_JWT` and posts to the adapter registry (LOC8).

## Adapter registry (LOC8)

**Settings → LLM keys → Local adapter registry** — register Ollama tags, activate one slug for routing hints. Imported models appear in Local Inference configured slugs list.

## Dataset Recipe wizard (LOC6)

**Settings → LLM keys → Dataset Recipe wizard**

1. Upload `.csv` (question/answer columns), `.pdf`, or `.txt`/`.md`
2. **Generate Q&A** — local model only (`local_sovereign` or `LLM_AIRGAP=1`)
3. **Approve all** — HITL gate before export
4. **Export JSONL** — merge with LOC5 verified export for Unsloth fine-tune

## Sovereign recipe hints (LOC14)

**Settings → LLM keys → Sovereign recipe hints · local-adapter**

- Tag recipes with `local-adapter` when registering an adapter (`link_recipe_ids`)
- In `local_sovereign` routing, semantic recipe search boosts tagged recipes
- Panel lists imitation hints for operator session routines

## Fine-tune queue (LOC9)

**Settings → LLM keys → Fine-tune queue · GPU worker**

1. Export verified JSONL (LOC5) to `/app/exports/finetune/tenant-{id}/verified-dataset-latest.jsonl`
2. **Create draft** — adapter name + base model
3. **Approve & enqueue** — HITL gate; Celery `gpu_finetune` worker runs simulation (default) or host script when `LOCAL_FINETUNE_EXECUTE=1`
4. Import GGUF via LOC7 bridge + register adapter LOC8

GPU worker (optional):

```bash
docker compose -f docker-compose.yml -f docker-compose.local-gpu.yml up -d celery-gpu-worker
```
