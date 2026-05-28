# RoundtableSpace May 2026 — Prehodnotenie + Queenswarm roadmap

Updated: 2026-05-21  
Zdroj: 4 posty (20.–21. mája 2026) — Graphify, Claude rerouter, Venice MCP, Overnight Life OS.

## Verdikt

Analýza **potvrdzuje smer** Queenswarmu. Konkurencia rieši jednotlivé body (graph, lacný LLM, MCP tools, overnight triage), ale **nikto nemá náš stack naraz**:

| Naša výhoda | Prečo to konkurencia nekopíruje lacno |
|-------------|----------------------------------------|
| Persistent Hive Mind (Neo4j + pgvector + Obsidian vault) | Free reroutery nemajú pamäť → hallucinated repo state |
| Verified loop (simulate → reward → recipe) | Overnight skripty dávajú raw output bez guardrails |
| LiteLLM + CostGovernor + tenant RBAC | Hack reroutery nemajú billing, audit, tier gates |
| Dynamic MCP hub + marketplace | Venice MCP je jeden provider, nie orchestrovaný swarm |

**Nepotrebujeme novú architektúru** — potrebujeme **viditeľné „wow“ UX** na existujúcich moduloch.

---

## Post 1 — Graphify (folder → knowledge graph)

**Ich ponuka:** Folder → searchable graph + Obsidian wiki → 40–70 % token savings.

**Čo už máme (≈70 %):**

- Neo4j knowledge graph — `/api/v1/hive-mind/graph`
- pgvector/Chroma semantic search — `/api/v1/hive-mind/search`
- Obsidian vault sync — `phase3_obsidian_watch_enabled`, `hive_mind_vault_root`
- Foragers ingest pipeline — `/foragers`
- Graph export limits + cache — `hive_mind_max_graph_export_nodes`

**Čo chýba (lacno, bez fork Graphify):**

| Feat | Popis | Odhad | Závislosti |
|------|-------|-------|------------|
| **Auto-Graphify ingest** | Jeden folder / zip upload → nightly forager + Obsidian watch → graph nodes | 5–7 dní | Foragers, Obsidian watch |
| **Selective recall mode** | Namiesto full context dump: graph-neighbor RAG + token budget cap | 3–4 dni | `hive_mind_max_prompt_chars`, LLM router |
| **Project shape map** | Vizualizácia štruktúry projektu (adresáre, moduly, stale nodes) na `/knowledge` | 4–5 dní | Graph API + frontend graph component |

**Úprava odhadu oproti pôvodnej analýze:** 7–10 dní → **5–7 dní**, lebo rebuild Graphify netreba — len UX + ingest hook.

**Metrika úspechu:** merateľný pokles `tokens_in` na verified workflow (CostRecord) o ≥30 % pri rovnakej kvalite simulácie.

---

## Post 2 — Free Claude Code rerouter

**Ich ponuka:** Presmerovanie na 10 free providerov (DeepSeek, Kimi…).

**Čo už máme (lepšie, ale quality-first):**

- `LiteLLMRouter` — Grok → Claude → GPT chain (`llm_router.py`)
- `CostGovernor` — daily budget block + Prometheus metriky
- `/costs` dashboard + `CostRecord` ledger
- Per-tenant LLM keys settings

**Čo chýba:**

| Feat | Popis | Odhad | Diferenciácia |
|------|-------|-------|---------------|
| **Free-First routing mode** | Settings: `quality` \| `economy` \| `free_first` — jednoduché tasky → lacné modely | 2–3 dni | Hive Mind drží kontext aj pri cheap model |
| **Cost Guardian auto-upgrade** | Po N failoch / low confidence → upgrade chain hop | 2 dni | Reroutery nemajú fallback s pamäťou |
| **Token savings ledger** | „Ušetril si $X vs quality baseline“ v dashboarde | 2–3 dni | Viazané na existujúci `/costs` |

**Kritická poznámka:** Neintegrovať sketchy GitHub rerouter. Použiť **LiteLLM natívne modely** + env keys (`DEEPSEEK_API_KEY`, atď.). Marža zostáva pod našou kontrolou.

**Biznis:** Umožní **generous free tier** alebo nízku vstupnú cenu bez straty kontextu.

---

## Post 3 — Venice MCP (31 tools)

**Ich ponuka:** Oficiálny MCP server — chat, image, video, audio, web search.

**Čo už máme:**

- Dynamic Connector Hub — OAuth, vault, MCP manifests
- Tools Marketplace — one-click Phase 3 template install
- `MCPAdapter.dynamic_tool_catalog()` — flatten tools pre supervisor
- Integrations hub — `/integrations?tab=hub|marketplace`

**Čo chýba:**

| Feat | Popis | Odhad |
|------|-------|-------|
| **Venice MCP preset** | Phase 3 template „Venice“ v marketplace (nie nový hub) | 1–2 dni |
| **Unified Tool Hub UI** | Jeden panel: všetky MCP tools + cena/rýchlosť hint | 3–4 dni |
| **Tool Discovery Loop** | Forager job: scan nových MCP serverov → návrh do marketplace | 3–5 dní |

**Úprava priority:** P1, nie P0 — hub existuje, chýba preset + discovery automation.

---

## Post 4 — Overnight folder → Life OS (najväčší viral win)

**Ich ponuka:** Dump folder pred spaním → ráno tasky, stalled projects, briefing.

**Čo už máme (≈60 %):**

- `DreamerService` + Celery `run_memory_dreaming`
- Nightly routines — `SupervisorRoutine` interval scheduler
- `DreamingSummaryCard` na dashboarde
- Ballroom voice pipeline — STT/TTS config
- Supervisor session → playbook save (verified workflow)

**Čo chýba:**

| Feat | Popis | Odhad | Viral factor |
|------|-------|-------|--------------|
| **Dump & Sleep** | Ballroom / mobile: upload folder + voice note → overnight queue | 3–4 dni | ⭐⭐⭐⭐⭐ |
| **Life OS template** | Swarm Builder template — triage + priorities + morning routine | 1–2 dni | ⭐⭐⭐⭐ |
| **Overnight Swarm Report** | Ráno: summary card + pollen earned overnight | 2 dni | ⭐⭐⭐⭐ |
| **Voice morning briefing** | Ballroom TTS: „Ušetril som ti 3h, 7 stalled taskov…“ | 2–3 dni | ⭐⭐⭐ (P2) |

**Prečo P0:** Priamo reaguje na najhorúcejší post; využíva existujúci Dreaming modul.

---

## Odporúčané poradie (ROI × náklady × existujúce assety)

| Priorita | Feature | Odhad | Náklady | Impact | Poznámka |
|----------|---------|-------|---------|--------|----------|
| **P0** | Dump & Sleep + Overnight Report polish | 3–5 dní | ~0 | Viral + retention | Dreaming + Celery hotové |
| **P0** | Free-First + Cost Guardian UX | 2–3 dni | 0 | Akvizícia + marža | LiteLLM + CostGovernor hotové |
| **P1** | Auto-Graphify folder ingest + graph viz | 5–7 dní | nízke | Token savings + Pro upsell | Neo4j + Obsidian hotové |
| **P1** | Venice preset + Tool Discovery forager | 4–6 dní | 0 | MCP kompatibilita | Marketplace hotový |
| **P2** | Unified Savings Dashboard | 3–4 dni | 0 | Marketing ROI | `/costs` + time-saved existujú |
| **P2** | Voice Overnight Swarm Report | 2–3 dni | STT/TTS API | Wow moment | Ballroom voice hotové |

**Operator P0 (commercial lane + Hetzner) zostáva pred revenue launch** — product P0 vyššie môže ísť paralelne na `main` za feature flags.

---

## Mapovanie na existujúce assety

| Potreba | Už existuje | Súbor / route |
|---------|-------------|---------------|
| Nightly consolidation | ✅ | `dreamer_service.py`, `dreaming_tasks.py` |
| Graph RAG | ✅ | `hive_mind.py`, Neo4j driver |
| Obsidian ingest | ✅ | `phase3_obsidian_watch_enabled` |
| LLM routing | ✅ | `llm_router.py` |
| Cost control | ✅ | `cost_governor.py`, `/costs` |
| MCP tools | ✅ | `connectors.py`, `tools_marketplace.py` |
| Swarm templates | ✅ | `swarm-wizard-templates.ts` |
| Time saved ROI | ✅ | `time-saved-panel.tsx` |
| Foragers | ✅ | `/foragers` (Pro tier) |

---

## Feature flags (rollout)

Nové featury za `platform_features` / env until verified:

| Flag | Default | Tier |
|------|---------|------|
| `dump_sleep` | off | Pro+ |
| `free_first_routing` | off | Free (economy), Pro (optional) |
| `auto_graphify` | off | Pro+ |
| `tool_discovery_loop` | off | internal |
| `overnight_voice_report` | off | Pro+ |

---

## Audit gates (Fáza 4)

| Feat | Gate script (planned) |
|------|----------------------|
| Dump & Sleep | `./scripts/mission-phase4-dump-sleep-audit.sh` |
| Free-First routing | `./scripts/mission-phase4-routing-audit.sh` |
| Auto-Graphify | `./scripts/mission-phase4-graphify-audit.sh` |
| MCP discovery | `./scripts/mission-phase4-mcp-audit.sh` |

---

## Referencie

- `docs/ROADMAP.md` — P4 RoundtableSpace edge
- `docs/MISSION_EXECUTION_BACKLOG.md` — Fáza 4 tabuľka
- `frontend/lib/platform-capabilities-catalog.ts` — Capabilities Atlas planned entries
- `frontend/lib/swarm-wizard-templates.ts` — Life OS template (coming soon)
