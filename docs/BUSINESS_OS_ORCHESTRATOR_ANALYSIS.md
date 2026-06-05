# Business OS Orchestrator — analýza a roadmap fit

Updated: 2026-06-05  
Zdroj požiadavky: [0xTria X post](https://x.com/0xTria/status/2061813514893668735) (obsah nebol priamo načítateľný — 403); rekonštrukcia z popisu operátora + ekosystémových vzorov ([ZeroInc](https://github.com/agentxagi/zero-inc), [Zero-Human Company anatomy](https://bingran.ai/zero-human-company), [Agentic heartbeat pattern](https://www.mindstudio.ai/blog/agentic-os-heartbeat-pattern-proactive-ai-agent/)).

**Cieľ:** Hlavný orchestrátor/pomocník pre biznis v Queenswarm — radí čo robiť, časť vecí organizuje sám cez tím agentov. **Nie implementácia teraz** — len čo sa oplatí a čo reálne využijeme.

---

## 1. Čo také systémy typicky sľubujú (2026 konvergencia)

| Vrstva | Popis | Príklad |
|--------|--------|---------|
| **Control plane** | Jeden „CEO“ pohľad: ciele, rozpočet, schválenia | ZeroInc dashboard |
| **Goal alignment** | Každá úloha má stopu k misii firmy | „$1M MRR“ → tasky |
| **Heartbeat team** | 3–15 agentov na cron-e: kontrola fronty, akcia, report | Marketing / Revenue / Ops bees |
| **Governance** | Človek schvaľuje peniaze, publish, live | Approval gates |
| **Audit** | Ticket trace, tool-call log | Session + mission lineage |
| **BYO runtime** | Cursor, Codex, OpenClaw ako „zamestnanci“ | HTTP heartbeat adapter |

**Čo je hype a neberieme celé:** „zero humans“, plná org chart UI pre 20 rolí, cross-chain platby agentov, generický chatbot bez simulate-first.

---

## 2. Čo Queenswarm už má (silný základ)

| Potreba z X/ZeroInc | U nás dnes | Kde |
|---------------------|------------|-----|
| Ranný brief „čo robiť“ | ✅ | `GET /solo-operator/morning-brief`, Operator Loop |
| Denný plán (lanes) | ✅ | `solo_daily_plan` — PO, marketing, trading, ops |
| Mission visibility | ✅ | Mission Kanban `/tasks`, ⌘K search |
| Background digesty | ✅ | Four Lanes (marketing, SCV, eshop, automation) |
| Orchestrátor session | ✅ | Supervisor sessions — **kanonická cesta** |
| Náklady / throttle | ✅ | CostGovernor, `/costs` |
| Simulate-first | ✅ | Guardrails, publish lane, trading paper |
| Revenue pipeline | ✅ | Factory → gumroad-ready → `letagentscook.org` |
| Pamäť / kontext | ✅ | Brain Pack, curated memory, HiveMind |
| Control plane akcie | ✅ čiastočne | Operator Control Plane (`start_day`, `run_trio`) |
| Virtual Company šablóny | ⚠️ legacy | Deprecované pre solo primary UX — kód ostáva |

**Záver:** ~60–70 % „Business OS“ už existuje, ale je **roztrúsené** (Settings harness, Agentic OS Lanes, Mission Control, Factory). Chýba **jeden hlavný biznis orchestrátor** s jasnou hierarchiou: *radí → schvaľuješ → tím beží sám v povolených lane*.

---

## 3. Gap — čo by sme reálne využili

### Berieme (P1–P2)

| ID | Názov | Prečo | Odhad |
|----|-------|-------|-------|
| **BA1** | **Chief Business Operator (CBO)** | Jeden panel v Cockpit: revenue status, Gumroad queue, top 3 akcie | ✅ shipped |
| **BA2** | **Business Goal Stack** | Tenant ciele (MRR/listings/trading paper) → misie auto-tagged, CBO meria drift | ✅ shipped |
| **BA3** | **Background Business Team (3 bees)** | Marketing Ops · Revenue Ops · Factory Ops — heartbeat cron, nie nový org chart | ✅ shipped (`BUSINESS_BACKGROUND_TEAM_ENABLED`) |
| **BA4** | **Unified Approval Inbox** | Jedna fronta: publish, Gumroad upload, lane digest, agent suggestions | ✅ shipped |
| **BA5** | **Proactive Pulse** | Ráno (máme) + **obedný** pulse: čo sa zmenilo, čo bežalo autonómne | ✅ shipped |
| **BA6** | **CBO → Dispatch bridge** | Z CBO jeden klik: triage+dispatch s predvybraným skill bundle (bez výberu 20 agentov) | ✅ shipped |
| **BA7** | **Cross-lane learning** | Trading/marketing recipe winner → CBO navrhne „apply to lane X“ | 3–4 d |
| **PA2** | **Google Calendar** | Proaktívny denný plán s kalendárom (už v pláne) | 3–5 d |

### Neberieme (alebo P4+)

| Nápad | Dôvod odmietnutia / odklad |
|-------|----------------------------|
| 15+ agentov 24/7 bez cap | Náklady LLM, chaos; cap **3–5 background bees** + sessions on-demand |
| Plná org chart UI | Nízka hodnota vs Mission Kanban + lane status |
| Nahradiť Supervisor session | Porušuje [OPERATOR_CANONICAL_WORKFLOW.md](OPERATOR_CANONICAL_WORKFLOW.md) |
| Blockchain / x402 platby agentov | Mimo revenue priority (Gumroad first) |
| Multi-company ZeroInc izolácia | B2B neskôr; solo operator first |
| Autonómny Gumroad publish bez schválenia | Porušuje simulate-first + cash risk |

---

## 4. Navrhovaná architektúra (file-based + skills)

```
Tenant goals (Postgres + curated memory)
        ↓
Chief Business Operator (CBO) — 1 bee, 1 job
  ├─ read: revenue status, mission kanban, lanes, gumroad queue
  ├─ propose: top 3 actions (structured JSON)
  └─ act (gated): dispatch bundle, run trio, pause lane
        ↓
Background Business Team (max 3 heartbeats)
  ├─ marketing_ops_bee   → digest, draft, publish queue (simulate)
  ├─ revenue_ops_bee     → gumroad scorecard, listing gaps, UPLOAD_QUEUE
  └─ factory_ops_bee     → factory readiness, batch suggest
        ↓
Supervisor sessions (execution engine — unchanged)
        ↓
Approval Inbox → verified → Recipe Library + pollen
```

**Skill pack (budúci Gumroad/harness):** `/business-os-orchestrator` — CBO prompt + approval checklist + heartbeat recipes.

**MCP-like surface:** `GET /api/v1/business-operator/snapshot`, `POST /business-operator/act`, `GET /business-operator/approvals`.

---

## 5. UX — kde to žije

| Surface | Úloha |
|---------|--------|
| **Cockpit → Business OS** (nový panel, nie nový primary nav) | CBO brief + approvals + „Run team“ |
| **Mission Control** | Stále visibility; CBO len posiela dispatch |
| **Settings harness** | Ciele, rozpočet per bee, heartbeat schedule |
| **Mobile** | Ranný/obedný push z Proactive Pulse |

**Desktop:** bez zmeny sidebar layoutu — panel v Cockpit (konzistentné s Operator Control Plane).

---

## 6. Bezpečnosť a anti-slop

- Všetky CBO **akcie s write/publish/financial** → `requires_approval` + Trust lane  
- CBO **nikdy** neposiela bank/PII do LLM (reuse solo PO guard)  
- Background bees: **simulate default**; live len po explicit operator approve  
- Každý heartbeat výstup → **simulation alebo scorecard** pred zobrazením operátorovi  
- Adversarial critic na CBO „top 3“ keď stakes > threshold (Gumroad copy, trading)

---

## 7. Fázovanie (odporúčanie)

| Fáza | Scope | Závislosť |
|------|-------|-----------|
| **BA1** | CBO snapshot API + Cockpit panel (read-only brief) | revenue status, daily plan, gumroad queue |
| **BA4** | Approval Inbox (merge existujúcich front) | publish queue, suggestions |
| **BA6** | Dispatch bridge z CBO | Mission Kanban OW13 |
| **BA3** | 3 heartbeat bees (wrap Four Lanes + factory) | FL1–FL5 |
| **BA2** | Goal Stack | curated memory |
| **BA5** | Midday pulse | Telegram gateway |
| **BA7** | Cross-lane learning | imitation v2, recipes |
| **PA2** | Calendar | OAuth Google |

**Priorita voči cash:** BA1 → BA4 → BA6 pred BA3 deep automation.

---

## 8. Mapovanie na existujúce roadmap IDs

| Staré ID | Nové / rozšírenie |
|----------|-------------------|
| PA1 Business Assistant cockpit | → **BA1 + BA4** (konkrétnejšie) |
| PA2 Google Calendar | → **PA2** (bez zmeny) |
| AOS1 harness profiles | → CBO používa marketing/factory/trading profile |
| AOS2 mission agent picker | → **BA6** (CBO auto-pick max 3–5) |
| FL1–FL5 Four Lanes | → **BA3** background team (nie duplicita — wrap) |

---

## 9. Referencie

- [0xTria post](https://x.com/0xTria/status/2061813514893668735) — primárny podnet (obsah nedostupný pri scrape)
- [ZeroInc GitHub](https://github.com/agentxagi/zero-inc) — goal + hire team + heartbeat + governance
- [Zero-Human Company anatomy](https://bingran.ai/zero-human-company) — control plane vs agent labor layer
- [MindStudio heartbeat pattern](https://www.mindstudio.ai/blog/agentic-os-heartbeat-pattern-proactive-ai-agent/) — proactive OS, nie chat-on-demand
- Interné: [OPERATOR_CANONICAL_WORKFLOW.md](OPERATOR_CANONICAL_WORKFLOW.md), [CAPABILITIES_SYNTHESIS_MAY2026.md](CAPABILITIES_SYNTHESIS_MAY2026.md)
