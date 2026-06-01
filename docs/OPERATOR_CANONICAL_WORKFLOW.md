# Queenswarm — Kanonický operátorský workflow

Updated: 2026-06-01  
Status: **Jediná oficiálna cesta** pre solo operátora na queenswarm.love.

Ostatné panely (Four Lanes, Swarm Fleet, ICM, Futurist modules…) sú **voliteľná automatika alebo pokročilé nástroje** — nie hlavný spôsob spustenia práce.

---

## 0. Mental model (60 sekúnd)

| Pojem | Čo to je | Používaš denne? |
|-------|----------|-----------------|
| **Supervisor session** | „Urob túto vec teraz“ — researcher, critic, designer… | **ÁNO — hlavné tlačidlo** |
| **Mission Control** (`/tasks`) | Kanban Triage→Done, dispatch, lineage, workspace | **ÁNO — prehľad misií** |
| **⌘K / Ctrl+K** | Globálne hľadanie session + task | **ÁNO — rýchly skok** |
| **Task** | Sledovanie deliverable po schválení | Áno |
| **Curated memory** | Brief projektov + pravidlá pre Queen | Raz + pri novom projekte |
| **Routine** | Opakovaný cron (týždenný review) | Niekedy |
| **Forager** | Sťahovanie intelu z webu do HiveMind | Pozadie |
| **Four Lanes** | 4 automatické digesty | Voliteľné |
| **Sub-swarm** | Trvalá kolónia v DB (včely) | **Nemusíš** — infraštruktúra |

**Štart práce = Agents → Nová session s cieľom** alebo **Mission Control → Triage → Dispatch**. Nie Swarm Builder, nie Agentic OS Lanes.

---

## 1.5 Mission Control (Hermes-style Kanban)

URL: `/tasks` (solo režim: prvá položka v sidebar **Mission Control**)

| Stĺpec | Význam |
|--------|--------|
| **Triage** | Nové nápady / neštruktúrované požiadavky |
| **Ready** | Pripravené na dispatch |
| **In progress** | Beží session / swarm |
| **Blocked** | Čaká na vstup operátora |
| **Review** | Critic / simulate gate |
| **Done** | Overené deliverable |

**Rýchle akcie:**

- **Skill bundle chips** — Content week, Landing page, Research sprint, Campaign brief (triage + dispatch jedným klikom)
- **Dispatch** — spustí Workflow Breaker + tracer slices (execution engine = supervisor session)
- **Task drawer** — Parents/Children lineage, operator notes, workspace súbory
- **⌘K / Ctrl+K** — globálne hľadanie session + task (aj z Knowledge search panelu)

**Pravidlo:** Kanban je **visibility layer** — skutočná práca stále beží cez **Agents → Sessions**. Kanban nenahradzuje session engine.

---

## 1. Jednorazové nastavenie (Setup once)

### 1.1 Prihlásenie a bezpečnosť

1. `/login` — email + heslo  
2. Google Authenticator (2FA) — pri prvom prihlásení  
3. **Settings → Security → Session policy** — „2FA re-verification“: **4 hours** (heslo stačí 4 h, potom znova Authenticator)

### 1.2 LLM kľúče (P0 — bez toho swarm nebeží)

**Settings → AI · LLM keys**

| Provider | Účel |
|----------|------|
| Grok (xAI) | Primárny model |
| Claude / GPT | Fallback |

Ulož → **Test** pri každom kľúči.

### 1.3 Research (odporúčané)

**Integrations** — Tavily alebo ekvivalent pre web research v session.

### 1.4 Notifikácie (voliteľné)

**Settings → Execution Studio → Notifications**

- Email (denný prehľad práce)  
- Telegram (okamžité pingy)

### 1.5 Auto-approve (solo operátor)

**Agents → Sessions → Auto-approve ON**

- Rutinné digesty schvaľuje systém  
- Kritické veci (billing, prod deploy) stále manuálne

### 1.6 Project briefs (Knowledge)

**Knowledge → Curated memory**

Pre každý veľký projekt blok v **Instructions** alebo samostatný súbor:

```markdown
PROJECT: [názov]
Cieľ: [čo má vzniknúť]
Deliverables: [konkrétne výstupy]
Jazyk: SK/CZ/EN
Simulate-first: áno — nič live bez approve
Deadline fázy: [dátum]
```

Queen to injectuje do každej novej session.

---

## 2. Hlavný workflow — spusti projekt (krok za krokom)

### Krok 1 — Otvor Agents

URL: `/agents`  
Sekcia: **Supervisor sessions** (horný formulár „Session goal“).

### Krok 2 — Napíš cieľ (Goal)

Formát: **Goal → Context → Constraints → Done**

Príklad (web redesign, fáza 1):

```
PROJECT: Web Redesign 2026 — Phase 1 Discovery

Úloha:
1. Audit súčasného webu (UX, SEO, rýchlosť) — verejné zdroje.
2. Benchmark 5 konkurentov.
3. Navrhni IA max 12 stránok + MVP priority.
4. 3 varianty homepage konceptu (text).

Výstup: report SK, max 1500 slov.
Critic APPROVE pred finálom. Simulate only.
```

### Krok 3 — Nastavenia session

| Pole | Odporúčanie | Prečo |
|------|-------------|-------|
| **Runtime** | `durable` pre veľké projekty | Nepadne pri refreshi |
| **Roles** | researcher + designer + critic | Analýza + návrh + verify |
| **Skills** | context, decide, tdd | Štandard |

### Krok 4 — Create session

Swarm beží. Sleduj stav: **running** → **completed** (alebo **needs_input** ak manuálny approve).

### Krok 5 — Prečítaj výsledok

Session riadok → **Info** → report / PDF  
Over critic review a excerpt.

### Krok 6 — Ďalšia fáza alebo Task

- **Fáza 2:** nová session s odkazom na fázu 1 („pokračuj z reportu S-XXXX“)  
- **Task:** manuálne v Tasks alebo Digest inbox → **→ Task**  
- **Mission Control:** presuň task medzi stĺpcami, pridaj operator note, otvor workspace deliverables

### Alternatíva — Mission Control first

1. `/tasks` → **Triage** — napíš krátky popis alebo vyber **skill bundle**  
2. **Dispatch now** — systém vytvorí session + task lineage  
3. Sleduj stĺpce **In progress → Review → Done**  
4. **⌘K** — nájdi starú session alebo task podľa kľúčového slova

### Paralelne viac projektov

**Každý projekt = samostatná session.** Môžeš mať 3–5 running naraz.  
Nemiešaj do jedného promptu 5 projektov.

---

## 3. Denný loop (5 minút)

1. **Email/Telegram** — denný prehľad (hotové / beží / manuálne)  
2. **Mission Control** (`/tasks`) — kanban stĺpce, blocked/review  
3. **Agents → Sessions** — filter **completed** — nové reporty  
4. **Info** na session — prečítaj, schváli ak treba  
5. **⌘K** — rýchly skok na task alebo session  
6. **Nová session** alebo **Dispatch** — ďalšia fáza projektu  

**Nepoužívaj:** Agentic OS ako prvý krok. **Nepoužívaj:** Swarm Builder pre bežnú prácu.

---

## 4. Mapa sekcií — čo používaš vs ignoruješ

| Sekcia | Použitie | Frekvencia |
|--------|----------|------------|
| **Agents** | Spúšťanie session, approve, reporty | **Denne** |
| **Mission Control** | Kanban, dispatch, lineage, workspace | **Denne** |
| **Tasks** | Deliverables, priority (table view) | Denne |
| **Knowledge** | Briefs, HiveMind, výstupy | Denne / týždenne |
| **Settings** | LLM, 2FA, notifikácie | Zriedka |
| **Integrations** | Tavily, OAuth publish | Pri potrebe |
| **Agentic OS** | Innovation Lab (tech návrhy), Lanes digest | Týždenne / voliteľne |
| **Apps & Tools** | Marketing/trading moduly | Keď riešiš danú doménu |
| **Ballroom** | Incident / realtime | Výnimočne |
| **Swarms / Fleet** | Legacy kolónie | **Ignoruj** (solo) |

---

## 5. Nastavenia — kompletný popis

### Settings → Security

| Nastavenie | Čo robí |
|------------|---------|
| **2FA (TOTP)** | Google Authenticator pri enrolli |
| **2FA re-verification** | Ako dlho stačí heslo bez OTP (napr. 4 h) |
| **Session policy — JWT TTL** | Ako dlho platí access token |
| **Session policy — Refresh TTL** | Ako dlho ostávaš prihlásený |
| **Auto-approve sessions** | Schvaľovanie rutinných session automaticky |

### Settings → AI · harness (Curated memory)

| Súbor | Obsah |
|-------|-------|
| **instructions** | Pravidlá operátora, jazyk, limity |
| **mission** | Poslanie hive |
| **ideal_state** | Cieľový stav |
| **soul / skills** | Tón a skill hierarchia |

### Settings → AI · LLM keys

API kľúče pre modely. Bez aspoň jedného kľúča session zlyhá.

### Settings → Execution Studio → Notifications

Email, Telegram, Slack webhooky pre digest a pingy.

### Settings → Platform

Feature flags tenantu — vypínaj moduly ktoré nepoužívaš.

### Agents panel

| Nastavenie | Čo robí |
|------------|---------|
| **Auto-approve** | Automatické schvaľovanie session |
| **Runtime inprocess/durable** | Dĺžka a odolnosť behu |
| **Roles** | Ktoré sub-agenty bežia |
| **Routines** | Cron opakovanie session |

---

## 6. Voliteľná automatika (nie hlavná cesta)

### Four Lanes (`/agentic-os#lanes`)

4 cron digesty. Bootstrap raz → potom len approve v Digest Inbox.  
**Nenahradzuje** ručné session pre veľké projekty.

### Foragers

Zber intelu (X, YouTube, RSS) → HiveMind. Session potom čerpajú kontext.

### Routines

Opakovanie rovnakého goal template (napr. týždenný campaign review).

---

## 7. Troubleshooting

| Problém | Riešenie |
|---------|----------|
| Session hneď **failed** | Skontroluj LLM kľúče Settings → AI |
| Prázdny report | Session ešte beží alebo sub-agent nemal výstup — pozri Ballroom events |
| Stále **needs_input** | Auto-approve off alebo kritická akcia — Approve v UI |
| 2FA pri každom logine | Security → 2FA window 4 h; po verify znova 4 h len heslo |
| Veľa možností v UI | Tento dokument — **ignoruj sekundárne panely** |

---

## 8. Súvisiace docs

- UI manual: `/manual#canonical-workflow`  
- Four Lanes detail: `docs/SOLO_OPERATOR_FOUR_LANE.md`  
- Solo mode: `docs/SOLO_OPERATOR_MODE.md`  
- Roadmap UX: `docs/ROADMAP.md` → Operator Workflow UX
