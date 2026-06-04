---
version: 1.0.0
priority: 88
roles:
  - supervisor
  - critic
  - evaluator
keywords:
  - model eval
  - nemotron
  - openrouter
  - llm router
  - long context
  - tool calling
reference_mode: true
references:
  - exports/model-evals/MODEL_EVAL_REPORT.md
---

# Model Eval Swarm

Use when deciding whether a new LLM should be promoted into Queenswarm routing.

## Purpose

Compare candidate models on Queenswarm-specific behavior before changing production defaults:

- long-context skill synthesis
- tool calling and recovery
- multi-step planning consistency
- guardrail preservation
- latency and cost envelope

## Guardrails

- No live customer action during eval.
- No secrets in prompts.
- Use redacted markdown fixtures from skills, progress files, and operator docs.
- Promote a model only after repeatable reports beat the current route on target scenarios.

## Default Candidate

`openrouter/nvidia/nemotron-3-ultra-550b-a55b:free`

## Operator Flow

1. Generate the eval plan: `python scripts/model_eval_swarm.py`.
2. Add `OPENROUTER_API_KEY` only in vault or `.env.prod.tokens`.
3. Run live model smoke/eval after token setup.
4. Save findings to `exports/model-evals/` and distill durable routing learnings.
