# Capabilities Synthesis — May 2026 (YouTube + X + Atlas)

Updated: 2026-05-25  
Zdroje: RoundtableSpace / levelsio / Hermes-style bookmarky, 32 YouTube videí, Capabilities Atlas, produkčný stav Queenswarm.

**North star:** Agent Operating System — self-improving hive, nie ďalší chatbot.  
**Bezpečnosť:** simulate-first · human approve pre live peniaze · PR-only self-maintenance.

---

## Čo už máme (silný náskok oproti CrewAI/AutoGen klonom)

| Oblasť | Stav | Kde |
|--------|------|-----|
| HiveMind + Neo4j + pgvector + selective recall | ✅ Live | Knowledge, `/hive-mind/*` |
| Dreaming + Dump & Sleep + overnight report | ✅ Live | Ballroom, Celery batch |
| Recipe Library + cosine 0.85 + imitation graph | ✅ Live | `/recipes`, Neo4j edges |
| LangGraph supervisor + dynamic spawn | ✅ Live | `/agents` |
| Pattern Router + Pattern Explorer | ✅ Live | `pattern_router.py`, harness |
| Behavioral memory (`instructions.md`) | ✅ Live | Settings → harness, Knowledge |
| Forager Intelligence Loop | ✅ Live | `POST /harness/intelligence-scan` |
| Queen Maintainer + Tech Health | ✅ Live | PR-only, tech-health API |
| Solo Operator (3 Bees, brief, session search) | ✅ Live | Settings harness |
| Publish lane A–K (queue, social, audit, performance) | ✅ Live | Execution Studio |
| Operator Loop (ranné veliteľské centrum) | ✅ Live | Settings harness |
| Trading Cockpit + Polymarket prep | ✅ Live | Execution Studio |
| Self-healing ops + Command Center | ✅ Live | Cron suite, monitoring |

**Záver:** ~70 % tém z analýzy už existuje. Medzery sú hlavne v **cross-swarm learning**, **trading swarm template**, **multi-model consensus**, a **revenue combo swarms**.

---

## Gaps vs. analýza (prioritizované)

### P0 — Autonómia & pamäť (Q2 2026)

| Gap | Prečo | Návrh implementácie |
|-----|-------|---------------------|
| **Cross-swarm knowledge transfer** | Trading learnings nejdú do marketing swarmu | Pollen winner → recipe auto-tag + HiveMind edge `learned_from_swarm`; Operator Loop navrhne „apply recipe X to marketing“ |
| **Imitation v2 (auto-neighbor)** | Cosine match je pasívny | Po 3× verified outcome rovnakého typu tasku → Imitation Engine prekopíruje top neighbor workflow do tenant suggestions (simulate pred apply) |
| **Dreaming → behavioral proposals** | Overnight batch neupravuje instructions | Dump & Sleep briefing generuje max 3 návrhy na `instructions.md` → operator 1-click approve v harness |

### P0 — Trading swarm (Q2 2026, Polymarket only)

| Gap | Prečo | Návrh |
|-----|-------|-------|
| **Trading Swarm Builder template** | Cockpit existuje, ale nie wizard | Nový template: Forager → Analysis → Risk → Executor bees; naviazané na Trading Cockpit lane |
| **Analysis Swarm (konsenzus)** | Jeden model = vyššie riziko | 3 cheap models (Grok mini + Claude haiku + GPT-4o-mini) → consensus bee; simulate-only default |
| **Risk Validator bee** | Live orders bez druhého názoru | Deterministic + LLM risk gate pred `execute_trade`; daily stop-loss sync s Cockpit |
| **Dreaming overnight trading review** | Žiadna nočná reflexia P&L | Celery 06:00 UTC: paper + audit fills → morning digest do Operator Loop |
| **Trade → Content pipeline** | Hybrid revenue z analýzy | Po verified paper fill / simulate trade → auto draft publish pack (faceless thread/short script) → Publish Queue |

### P1 — Marketing & obsah (Q3 2026)

| Gap | Návrh |
|-----|-------|
| **Content Flywheel 2.0** | Research forager → recipe match → critic → hook variants → Publish Performance feedback loop |
| **A/B hook optimizer** | Publish Performance + hook variants → odporúčať víťazný štýl per channel |
| **NotebookLM-style research bee** | Forager ingest URL/PDF → structured brief do HiveMind (nie raw dump) |

### P1 — Self-evolving harness (Q3 2026)

| Gap | Návrh |
|-----|-------|
| **Forager Intelligence v2** | Denný cron: MCP manifest diff + skill stale detection + auto PR draft cez Queen Maintainer |
| **Pattern Router LLM** | Flag ON pre power users; heuristic fallback; Pattern Explorer ukazuje „why“ |
| **Recipe marketplace beta** | UGC recipes s revenue share; overené trading/marketing workflowy |

### P2 — Biznis combo swarms (Q4 2026 – 2027)

| Nápad | Popis | Technická zvládnuteľnosť |
|-------|-------|--------------------------|
| **Trading + Content Hybrid** | Jeden swarm: paper/live Polymarket + auto content o výsledkoch | ✅ High — stava na Operator Loop + publish lane |
| **Life OS + Business OS bundle** | Ráno brief + stalled + publish + trading v jednom preset | 🔄 Partial — Operator Loop; **BA1 CBO** + **BA4 Inbox** (see `BUSINESS_OS_ORCHESTRATOR_ANALYSIS.md`) |
| **Public Trading Transparency** | Verejný dashboard P&L (paper first) | ✅ Medium — read-only snapshot, no secrets |
| **Faceless Media Agency in a Box** | White-label publish lane pre klientov | ✅ Medium — multi-tenant onboarding už čiastočne |
| **Micro-SaaS Factory** | Swarm postaví landing + monetization lane + deploy | ⚠️ Lower — veľký scope; fáza 2+ |
| **Skill Marketplace 2.0** | Performance fee na overených recipes | ✅ Medium — billing flags existujú |

---

## Odporúčané workflowy (best practice 2026)

### Trading (Polymarket)

```
Forager (markets) → HiveMind recall → Pattern Router (Review Loop)
  → Analysis Swarm (3-model consensus) → Risk Validator
  → Dreaming overnight check → Paper tick / Live (human approve)
  → Reflect → Recipe save → Trade→Content draft (optional)
```

### Marketing / publish

```
Research forager → Recipe match (≥0.85) → Content Flywheel swarm
  → Critic verify → Hook variants → Publish Queue approve
  → Simulate → Publish Performance insights → Trusted auto (optional)
```

### Self-evolution (vždy)

```
Execute → Simulate sandbox → Human approve (high risk)
  → Reflect → Pollen → Recipe Library → Imitation neighbor
  → Queen Maintainer (code) / Forager v2 (skills/MCP)
```

---

## 6–12 mesiacov — must-have poradie (dev)

1. **Trading Swarm template** + Analysis + Risk bees  
2. **Cross-swarm recipe transfer** + Imitation v2  
3. **Trade → Content pipeline**  
4. **Dreaming behavioral proposals**  
5. **Content Flywheel 2.0** + A/B hook optimizer  
6. **Forager Intelligence v2**  
7. **Recipe marketplace beta**  
8. **Public paper-trading transparency** (brand)  

Operator-only (bez dev): Polymarket CLOB vault, first live post, Brain Pack daily use.

---

## Súvisiace docs

- [`ROADMAP.md`](ROADMAP.md) — P8 Autonomous Agent OS, P9 Revenue swarms  
- [`QUEENSWARM_DESIGN_PATTERNS.md`](QUEENSWARM_DESIGN_PATTERNS.md)  
- [`HARNESS_SELF_MAINTAINING_ANALYSIS.md`](HARNESS_SELF_MAINTAINING_ANALYSIS.md)  
- [`PRODUCTION_AUTOMATION_PHASES.md`](PRODUCTION_AUTOMATION_PHASES.md)  
- [`OPERATOR_LOOP_MANUAL.md`](OPERATOR_LOOP_MANUAL.md)
