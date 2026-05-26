# Solo Operator — My 3 Bees, Brain Pack & Morning Brief

Návod pre **solo operátora** na queenswarm.love. Tieto featury **nerozbíjajú hive** — sú tenká orchestrácia nad tým, čo už máš.

**Kde v UI:** Settings → **AI harness** (trio + publish onboarding) · Knowledge → **Curated memory** (brain pack)

---

## Prečo to existuje (vs Hermes)

| Hermes | Queenswarm ekvivalent | Náš rozdiel |
|--------|----------------------|-------------|
| `SOUL.md` + `MEMORY.md` + `USER.md` | **Operator Brain Pack** | Rovnaké tri vrstvy, ale **verify-first** + swarm-wide pamäť |
| Cron → Telegram brief | **Morning Hive Brief** + trio cycle | Brief z **overených** session, nie raw LLM |
| 3 agent profily | **My 3 Bees** (mini-swarm **skupina**) | Nevytvára nový hive — len bindne **existujúce routines** |
| FTS session search | **Hive Session Search** | Hľadá cez **celý swarm** (goals + sub-agent summaries) |
| Self-evolving skills | **Verified Skill Forge** | Skill až po **critic APPROVED** → pending v Execution Studio |

**Filozofia:** Hermes vyhráva na jednoduchosti jedného agenta. My vyhrávame na **overenom swarme**, grafe a SCV — trio ti dá Hermes-feeling bez straty existujúceho setupu.

---

## My 3 Bees — čo to je a čo to **nie je**

### ✅ Je to

- **Preset skupina** — tri „lanes“ (Hive Learner · SCV Maintainer · Life OS)
- **Orchestrátor** existujúcich `SupervisorRoutine` riadkov v DB
- Tlačidlo **Run today's cycle** = spustí bound routines **postupne**
- **Morning brief** = prečíta posledné completed session + tech health score

### ❌ Nie je to

- Nový sub-swarm ani noví bees
- Náhrada Virtual Company / 28-bee hive
- Automatické vytváranie swarmov (ak routine chýba, UI ukáže hint)

### Ako sa routine bindne

Priorita:

1. **`context_payload.solo_trio_lane`** — explicitný tag (API `PUT /solo-operator/trio/bind`)
2. **Názov routine** — pattern matching:

| Lane | `solo_trio_lane` | Názov obsahuje (príklad) |
|------|------------------|--------------------------|
| Hive Learner | `hive_learner` | sentinel, hivemind learning |
| SCV Maintainer | `scv_maintainer` | queen maintainer, scv |
| Life OS | `life_os` | life os, morning briefing, overnight |

**Tvoj sentinel routine** sa typicky bindne sám (názov „Daily sentinel scan“).

---

## Rýchly štart (15 min)

### 1. Deploy (ak ešte nie je na prod)

```bash
cd /root/Queenswarm
docker compose -p queenswarm_prod \
  -f docker-compose.base.yml -f docker-compose.prod.yml \
  --env-file .env.prod build backend frontend celery-worker
docker compose -p queenswarm_prod \
  -f docker-compose.base.yml -f docker-compose.prod.yml \
  --env-file .env.prod up -d backend frontend celery-worker
```

### 2. Brain Pack — kto je tvoj agent

**Knowledge → Curated memory** (tab Memory)

| Tab | Súbory | Čo tam napísať |
|-----|--------|----------------|
| **SOUL** | `soul`, `skills_hierarchy` | Identita, tón, priorita skills |
| **MEMORY** | `mission`, `ideal_state` | Projekty, fakty, ciele hive |
| **USER** | `instructions` | Tvoje preferencie: jazyk, limity, approve pravidlá |

**Rýchlo:** tlačidlo **Load starter pack** — predvolené texty pre solo operátora (len prázdne polia). API: `POST /api/v1/memory/curated/seed-brain-pack`.

**Hint:** Export → tlačidlo **Export .md** skopíruje celý pack do clipboardu (backup / Notion).

**Social OAuth:** `docs/OPERATOR_SOCIAL_OAUTH_SETUP.md`

Queen a supervisor sessions čítajú tieto súbory pri bootstrap — **nemusíš** nič meniť v kóde.

### 3. Skontroluj trio binding

**Settings → AI harness** → karta **My 3 Bees**

- Zelený badge **3/3 lanes bound** = ideál
- **1/3** alebo **2/3** = chýba swarm/routine pre danú lane

**Ak chýba lane:**

| Chýba | Urob |
|-------|------|
| Hive Learner | Už máš sentinel routine → malo by byť OK. Ak nie: Swarm Builder → **Sentinel Radar** |
| SCV Maintainer | Queen Maintainer routine (`bootstrap_queen_maintainer_routine.py` alebo Settings harness) |
| Life OS | Swarm Builder → **Life OS** template (overnight + morning brief) |

### 4. Spusti dnešný cyklus

1. **Settings → AI harness → Run today's cycle**
2. Sleduj **Agents / Ballroom** — tri session-y (alebo menej, ak niečo unbound)
3. Pre Hive Learner očakávaj: researcher → critic → `hivemind_verify_status: approved`
4. **Morning brief** — tlačidlo v tej istej karte; digest z posledných completed výstupov

### 5. Session search — „čo sme riešili minulý týždeň?“

**Knowledge → Curated memory** → **Hive session search**

- Min. 2 znaky: `sentinel`, `maintainer`, `stalled`, …
- Klik na session ID → `/agents?session=…`

### 6. Bank PO — supervisor quick-start

**Dashboard → Dnešný plán** alebo **`/agents?preset=bank-po-brief`**

| Preset | URL | Účel |
|--------|-----|------|
| Stakeholder brief | `/agents?preset=bank-po-brief` | Status, riziká, asks |
| Backlog review | `/agents?preset=bank-po-backlog` | PI/backlog priorizácia |
| Marketing draft | `/agents?preset=marketing-draft` | Publish pack → simulate |
| Paper trading | `/agents?preset=paper-trading-review` | Paper cockpit review |

Na `/agents` v solo móde uvidíš aj tlačidlá **Solo quick-start** — vyplnia goal template automaticky.

**Pravidlo:** nikdy neposielaj citlivé bank dáta / PII do LLM — len anonymizované podklady (viď Brain Pack → Instructions).

**Bootstrap:** `./scripts/operator-solo-bootstrap-lane.sh` vytvorí/tagne trio routines + týždennú **Bank PO weekly brief** routine (pondelok 07:00 UTC).

---

## Denný / týždenný rituál (odporúčané)

| Kedy | Akcia | Kde |
|------|-------|-----|
| **Po deployi** | Brain Pack vyplniť / skontrolovať | Knowledge → Memory |
| **Ráno (Po–Pi)** | **Dnešný plán** (Dashboard) + 1× Bank PO session | Dashboard / `/agents` |
| **Ráno (Po–Pi)** | Run today's cycle **alebo** nech beží cron sentinel 06:00 | Settings harness |
| **Ráno** | Morning brief prehľad | Settings harness |
| **Po cycle** | HiveMind ingest + verify badge | Knowledge → HiveMind |
| **Týždenne** | SCV Maintainer (Queen Maintainer routine) | Execution Studio → approve PR proposal |
| **Po critic APPROVED** | Skontroluj **Verified Skill Forge** návrh | Execution Studio / agent suggestions |

---

## API (pre skripty / curl)

Všetko pod JWT (dashboard login):

```bash
# Status trio
GET /api/v1/solo-operator/trio

# Spusti cycle (všetky lanes)
POST /api/v1/solo-operator/trio/run
Body: {}   # alebo {"lane_ids": ["hive_learner"]}

# Explicit bind routine → lane
PUT /api/v1/solo-operator/trio/bind
Body: {"routine_id": "<uuid>", "lane_id": "hive_learner"}

# Morning digest
GET /api/v1/solo-operator/morning-brief

# Session search
GET /api/v1/solo-operator/session-search?q=sentinel&limit=15

# Brain pack export
GET /api/v1/memory/curated/export/brain-pack
```

---

## Časté otázky

**Rozbije mi trio existujúci hive?**  
Nie. Je to len zoskupenie **supervisor routines**. Bees a sub-swarms ostávajú.

**Musím mať presne 3 swarms?**  
Nie. Potrebuješ **3 routines** (môžu pochádzať z rôznych swarm templates). Jeden swarm môže mať viac routines.

**Prečo Life OS lane ukazuje „missing“?**  
Ešte nemáš Life OS swarm / morning routine. Build cez Swarm Builder — nič sa nesamovytvorí.

**Kde vidím výstup researcher+critic?**  
Ballroom event log · Learning Loop · Knowledge → HiveMind ingest · session search.

**Verified Skill Forge — čo s tým?**  
Po APPROVED ingest sa vytvorí pending `agent_suggestion` typu `verified_skill_forge`. Schváliš v Execution Studio → publish do Recipe Library / skills.

**Prečo nevidím „Factory“ v sidebar menu?**  
Skontroluj že `MICRO_SAAS_FACTORY_ENABLED=true` (solo preset od mája 2026 ho zapína default) a urob hard refresh. Factory je pod **Execution → Factory** (`/factory`) — spawn swarm, blueprint fázy, Execution Studio checklist.

---

## Publish lane → live (15 min Meta)

```bash
./scripts/operator-publish-live-rollout.sh
# docs/OPERATOR_PUBLISH_LIVE_15MIN.md
```

---

## Súvisiace docs

- `docs/SOLO_OPERATOR_MODE.md` — lockdown, IP, feature flags
- `docs/OPERATOR_RELEASE_RUNBOOK.md` — deploy + audit gates + týždenný checklist
- `docs/OPERATOR_QUICKSTART.md` — P0 release gates (solo: bez Stripe)
- `docs/PRODUCTION_AUTOMATION_PHASES.md` — Instagram / produkčné publish (budúce fázy)
- `docs/ROADMAP.md` — Fáza 7 Hermes-competitive
