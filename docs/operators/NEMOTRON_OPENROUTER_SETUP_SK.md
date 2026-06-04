# NVIDIA Nemotron cez OpenRouter — operátorský setup

Tento návod pripája NVIDIA Nemotron ako experimentálny model do Queenswarm. Nie je to default produkčný router, kým neprejde evalmi.

## Model

- Provider: OpenRouter
- LiteLLM slug: `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free`
- Token env: `OPENROUTER_API_KEY`

## Bezpečný postup

1. Vytvor OpenRouter API key.
2. Ulož ho mimo git:
   - preferované: Settings → AI / LLM keys → provider `openrouter`
   - alebo `.env.prod.tokens`: `OPENROUTER_API_KEY=...`
3. Over, že model je len eval kandidát, nie automatický live executor.
4. Spusti eval plán:

```bash
cd backend
python scripts/model_eval_swarm.py --out ../exports/model-evals/MODEL_EVAL_REPORT.md
```

5. Po token setup-e otestuj konkrétny model cez LLM keys test alebo samostatný eval smoke.

## Kedy ho povýšiť do routera

Povýšiť ho má zmysel až keď opakovane porazí aktuálny router v týchto scenároch:

- dlhý kontext nad viacerými skills/progress files
- tool recovery po zlyhaní nástroja
- multi-step planning bez straty guardrails
- business simulation bez nebezpečného autopricingu

## Čo nerobiť

- Nekomitovať `OPENROUTER_API_KEY`.
- Neprepínať production primary route len preto, že je model aktuálne free.
- Nepoužívať ho na live pricing alebo externé akcie bez simulácie a approval gate.
