# Queenswarm - Quick Start + Best Practices

Toto je praktický manuál pre teba ako hlavného používateľa Queenswarm. Je zameraný na rýchly štart, stabilnú prevádzku a konzistentné výsledky.

## 1. Quick Start

### Prihlásenie a prvé kroky

1. Otvor `https://queenswarm.love/login` a prihlás sa.
2. Po logine začni v `Dashboard`.
3. Skontroluj hornú navigáciu: `Dashboard`, `Agents`, `Tasks`, `Knowledge`, `Integrations`, `Ballroom`, `Settings`.

### Ako spustiť prvý Supervisor

1. Prejdi do `Agents`.
2. Otvor panel pre Supervisor session.
3. Zadaj cieľ jednou vetou (napr. „Analyze failing connector flow and propose safe fix“).
4. Doplň obmedzenia: „no breaking changes“, „include rollback“, „verify on staging first“.
5. Spusť session a sleduj stav (`running`, `needs_input`, `completed`).

### Základné ovládanie (denný rytmus)

1. `Dashboard`: rýchly prehľad stavu.
2. `Agents`: otvorené sessions, hlavne `needs_input`.
3. `Tasks`: priority a rozpracované úlohy.
4. `Knowledge`: predchádzajúce výsledky a kontext.
5. `Integrations`: stav kritických konektorov.
6. `Ballroom`: realtime koordinácia pri incidente.

## 2. Hlavné sekcie

### Dashboard

- Používaj ako centrálny prehľad pred každým väčším rozhodnutím.
- Sleduj, či všetky kľúčové časti aplikácie reagujú bez chýb.

### Agents + Supervisor

- Zakladaj Supervisor sessions pre komplexné úlohy.
- Pri stave `needs_input` reaguj rýchlo a jednoznačne.
- Každá session má mať jasný cieľ a očakávaný výstup.

Odporúčaný formát zadania:
- cieľ,
- kontext,
- obmedzenia,
- definícia hotového výsledku.

### Tasks + Routines

- `Tasks` používaj na jednorazové alebo projektové úlohy.
- `Routines` používaj na opakované procesy (denné/periodické kontroly).
- Ak sa proces opakuje aspoň 3x týždenne, presuň ho do routine.

### Knowledge

- Využívaj ako „retrieval-first“ vrstvu pred novým promptom.
- Over, či podobný výstup už neexistuje.
- Ukladaj sem finálne rozhodnutia, aby sa dali znovu použiť.
- V bloku `Memory + Dreaming` môžeš zapnúť automatickú konsolidáciu (default 24h), ručne ju spustiť a sledovať Dream Reports.

### Integrations

- Kontroluj dostupnosť a autorizáciu konektorov.
- Pri problémoch najprv testuj read-only operácie.
- Write operácie spúšťaj až po potvrdení zdravého stavu.

### Ballroom

- Používaj na realtime koordináciu počas incidentov a critical flowov.
- Drž komunikáciu stručnú: problém, rozhodnutie, ďalší krok.

## 3. Najlepšie praktiky

### Ako písať dobré prompty

Používaj štruktúru:
- **Goal**: čo presne má byť výsledok,
- **Context**: len podstatné fakty,
- **Constraints**: čo je zakázané alebo rizikové,
- **Done**: ako overíš, že výsledok je správny.

Príklad:
`Investigate 403 errors in consolidated sections, apply the safest fix without breaking auth flow, and include staging+production verification steps.`

### Ako šetriť zdroje

- Nepúšťaj viac náročných sessions naraz bez priority.
- Pri routines začni konzervatívnym intervalom a postupne dolaď.
- Pred novým výpočtom vždy skontroluj `Knowledge`.
- Pri zvýšenej záťaži zníž paralelizmus a uprednostni kritické workflow.

### Skills & retrieval

- Skill voľ podľa typu úlohy (debug, plan, review, execute).
- Najprv retrieval (`Knowledge`), až potom nový prompt.
- Po významnej zmene vždy over staging smoke/gates pred produkciou.

### Supervisor tipy

- Pri `needs_input` odpovedz jedným jasným rozhodnutím.
- Nemiešaj nesúvisiace témy do jednej session.
- Každú session uzavri konkrétnym výstupom (akčný plán/checklist/rozhodnutie).

## 4. Bežné scenáre

### Scenár A: Ranný 10-minútový startup

1. `Dashboard`: celkový stav.
2. `Agents`: otvorené sessions a `needs_input`.
3. `Tasks`: top priority na dnes.
4. `Integrations`: kritické konektory.
5. `Knowledge`: posledné relevantné outputs.

### Scenár B: Nový problém v produkcii

Use case: chyba v jednej sekcii po deployi.

1. V `Agents` založ Supervisor session s cieľom diagnostiky.
2. Pridaj obmedzenia: bez breaking changes, rollback povinný.
3. V `Tasks` založ task na implementáciu fixu.
4. Výsledok a verifikáciu zapíš do `Knowledge`.

### Scenár C: Zavedenie routine

Use case: denná kontrola stability integrácií.

1. V `Tasks + Routines` vytvor routine.
2. Definuj očakávaný výstup (napr. „daily integration health summary“).
3. Sleduj prvé behy a dolaď frekvenciu.
4. Ak routine neprináša hodnotu, uprav ju alebo vypni.

### Scenár E: Memory + Dreaming

1. V `Knowledge` otvor sekciu `Memory + Dreaming`.
2. Zapni Dreaming pre tenant a nastav frekvenciu (štandardne 24h).
3. Pri väčších zmenách spusti `Run Dreaming now`.
4. Skontroluj posledné Dream Reports a over, že nové lessons sú dostupné v Knowledge.

### Scenár D: Incident war-room

1. Potvrď symptóm (`Dashboard` + relevantná sekcia).
2. Spusť cieľenú session v `Agents`.
3. Koordinuj rozhodnutia v `Ballroom`.
4. Ulož postmortem kroky do `Knowledge`.

## 5. Troubleshooting

### Problém: po kliknutí ma vracia na login

- Over, že login prebehol úspešne.
- Skontroluj, či session cookie existuje.
- Ak je redirect, over `next` cieľovú cestu.

### Problém: 401/403 na `/api/proxy/*`

- 401 zvyčajne znamená problém so session/tokenom.
- 403 býva RBAC/permission guard.
- Over, že si prihlásený pod správnym tenant/rolou.

### Problém: session stojí na `needs_input`

- Otvor detail session v `Agents`.
- Odpovedz explicitne (Approve/Reject + presný pokyn).
- Vyhni sa všeobecným odpovediam bez rozhodnutia.

### Problém: routine nebeží

- Over, že routine je aktívna.
- Skontroluj posledný run a chybový detail.
- Over zdravie worker/beat komponentov.

### Problém: Integrations nevracajú dáta

- Over stav konektora v `Integrations`.
- Over auth/scope.
- Spusť read-only test pred write operáciou.

### Problém: app je pomalá

- Skontroluj `health` a `health/ready`.
- Over vyťaženie backend workerov.
- Dočasne zníž počet paralelných ťažkých úloh.

## 6. Memory + Dreaming (SK - podrobný manuál)

Táto sekcia je napísaná tak, aby ju pochopil aj úplný začiatočník.

### 6.1 Čo je Memory + Dreaming a na čo slúži

Memory + Dreaming je automatický "učebný režim" Queenswarmu:

1. prečíta posledné Supervisor sessions a udalosti,
2. nájde opakujúce sa úspechy aj chyby,
3. zlučuje duplicity,
4. vytvorí Dream Report,
5. uloží výsledok do HiveMind (`Knowledge`), aby sa systém učil z minulosti.

Jednoducho: systém sa každý deň (alebo podľa tvojho nastavenia) učí z vlastnej histórie.

### 6.2 Ako to zapnúť a nastaviť (krok za krokom)

1. Prihlás sa do dashboardu.
2. Otvor `Knowledge`.
3. Zroluj na blok `Memory + Dreaming`.
4. V poli `Frequency (hours)` nastav interval:
   - `24` = raz denne (odporúčané),
   - menšie číslo = častejšie učenie,
   - väčšie číslo = šetrnejší režim.
5. Klikni `Enable Dreaming`.
6. Ak chceš okamžitý beh, klikni `Run Dreaming now`.
7. Sleduj sekciu `Latest Dream Reports`.

Tip pre prvé nastavenie:
- nechaj `24`,
- zapni Dreaming,
- spusti 1 manuálny beh,
- over výsledok v reporte.

### 6.3 Čo to ovplyvňuje v aplikácii

Po zapnutí Memory + Dreaming sa mení hlavne toto:

- `Knowledge / HiveMind` dostáva nové konsolidované poznatky (Dream Reports),
- Supervisor sessions môžu ťažiť z lepšieho kontextu (menej opakovania rovnakých chýb),
- Routines plánovanie obsahuje pravidelný dreaming run pre tenant.

Čo sa nemení:

- nezmazávajú sa tvoje sessions,
- nevznikajú nebezpečné write zásahy bez explicitného flow,
- všetko ostáva tenant-scoped (jeden tenant nevidí dáta druhého).

### 6.4 Aký výsledok môže používateľ očakávať (príklady)

Príklad A - opakujúca sa chyba:
- systém nájde, že 4 sessions skončili na rovnakom auth probléme,
- v Dream Reporte to označí ako "repeated error",
- nabudúce vieš problém riešiť rýchlejšie podľa už známeho vzoru.

Príklad B - úspešná stratégia:
- systém vidí, že určitý postup pri connector incidente fungoval opakovane,
- uloží ho medzi "success strategies",
- tím má konzistentnejší postup pri ďalšom incidente.

Príklad C - duplicity:
- viac podobných výstupov sa zlúči do jedného insightu,
- výsledok je kratší, čistejší, prehľadnejší.

### 6.5 Výkon a spotreba zdrojov

Memory + Dreaming beží na nízkej priorite, ale stále používa výpočtové zdroje:

- CPU/worker čas: rastie pri častejšej frekvencii,
- DB/vektorové operácie: rastú s počtom sessions/eventov,
- pri `24h` intervale je režim bezpečne konzervatívny pre väčšinu tenantov.

Odporúčanie:
- začni na `24h`,
- ak máš veľa incidentov denne, skús `12h`,
- pod `6h` choď len keď máš jasný dôvod a sleduješ výkon.

### 6.6 Ako používať spolu so Supervisorom a Routines

Odporúčaný denný flow:

1. Supervisor rieši aktuálne úlohy a incidenty.
2. Počas dňa sa ukladajú session/event dáta.
3. Dreaming ich periodicky zhrnie do lessons.
4. Pri ďalšej Supervisor session máš lepší kontext v `Knowledge`.

Dobrá prax:
- po väčšom release alebo incidente vždy použi `Run Dreaming now`,
- potom otvoriť posledný Dream Report,
- najdôležitejší insight prepíš do interného postupu tímu.

### 6.7 Troubleshooting (najčastejšie problémy + riešenia)

Problém: `Latest Dream Reports` je prázdne.
- Skontroluj, či je Dreaming zapnutý.
- Klikni `Run Dreaming now`.
- Over, či existujú dáta zo sessions (ak nie sú, nie je čo analyzovať).

Problém: Dreaming je zapnutý, ale nebeží pravidelne.
- Over `Frequency (hours)`.
- Over, že routine nebola manuálne deaktivovaná.
- Over zdravie worker/beat.

Problém: Reporty sú príliš všeobecné.
- Potrebuješ viac kvalitných session vstupov.
- V Supervisor zadaniach píš presné ciele a výsledky.
- Po incidente doplň jasný kontext a uzáver.

Problém: výkon sa zhoršil.
- Zvýš interval (napr. z `6` na `24`).
- Nespúšťaj manuálne runy príliš často.
- Sleduj monitorovanie počas špičky.

---

## 7. Memory + Dreaming (EN - detailed guide)

This section is written for beginners, including users running the feature for the first time.

### 7.1 What Memory + Dreaming is and why it exists

Memory + Dreaming is Queenswarm's automatic self-learning loop:

1. reads recent Supervisor sessions and events,
2. detects repeated successes and failures,
3. consolidates duplicate patterns,
4. produces a Dream Report,
5. stores results into HiveMind (`Knowledge`) for future reuse.

In plain words: the system regularly learns from its own past work.

### 7.2 How to enable and configure it (step by step)

1. Sign in to the dashboard.
2. Open `Knowledge`.
3. Find the `Memory + Dreaming` panel.
4. Set `Frequency (hours)`:
   - `24` = once per day (recommended),
   - lower number = more frequent learning,
   - higher number = lower resource usage.
5. Click `Enable Dreaming`.
6. Optional: click `Run Dreaming now` for an immediate run.
7. Check `Latest Dream Reports` for outcomes.

First-time setup recommendation:
- keep `24`,
- enable Dreaming,
- trigger one manual run,
- review the first report.

### 7.3 What it affects inside the app

After enabling Memory + Dreaming:

- `Knowledge / HiveMind` receives new consolidated learning items,
- Supervisor sessions can use cleaner historical context,
- tenant routines include periodic Dreaming runs.

What it does not do:

- it does not delete your existing sessions,
- it does not bypass safety constraints,
- it stays tenant-scoped by design.

### 7.4 What results to expect (examples)

Example A - repeated failure pattern:
- multiple sessions fail on the same auth path,
- Dream Report marks it as a repeated error,
- future sessions can resolve it faster.

Example B - successful strategy reuse:
- a specific resolution strategy works repeatedly,
- Dream Report records it as a success pattern,
- operations become more consistent across incidents.

Example C - duplicate consolidation:
- many similar observations are merged,
- reports become cleaner and easier to act on.

### 7.5 Performance and resource impact

Dreaming runs at low priority, but still consumes resources:

- worker/CPU time increases with shorter intervals,
- DB/vector operations increase with larger history volume,
- `24h` is the safest default for most tenants.

Guideline:
- start with `24h`,
- use `12h` only when activity is high,
- go below `6h` only with clear operational need.

### 7.6 Using it together with Supervisor and Routines

Recommended operating loop:

1. Supervisor handles daily execution and incidents.
2. Sessions/events are persisted during operations.
3. Dreaming periodically consolidates those signals.
4. New Supervisor sessions benefit from improved Knowledge context.

Best practice:
- after major incidents/releases, run `Run Dreaming now`,
- review the newest report,
- turn top insights into repeatable team procedures.

### 7.7 Troubleshooting (common issues + fixes)

Issue: `Latest Dream Reports` stays empty.
- Verify Dreaming is enabled.
- Trigger `Run Dreaming now`.
- Confirm there is enough session/event data to analyze.

Issue: Dreaming enabled but no periodic runs.
- Check `Frequency (hours)`.
- Confirm routine is active.
- Verify Celery worker + beat health.

Issue: Reports are too generic.
- Improve Supervisor input quality (clear goals, outcomes, constraints).
- Add explicit post-incident conclusions.
- Let more sessions accumulate before evaluation.

Issue: noticeable performance impact.
- Increase interval (for example from `6` to `24`).
- Avoid excessive manual runs.
- Monitor worker load during peak traffic.

## 8. Voice Provider Settings (SK/EN)

### 8.1 SK - Nastavenie STT/TTS providerov v aplikácii

Nové voice nastavenie je dostupné v `Settings -> AI + Voice keys`.

1. Ulož API kľúče podľa potreby:
   - STT: `Grok` alebo `Deepgram` alebo `OpenAI`
   - TTS: `Grok` alebo `ElevenLabs` alebo `OpenAI`
2. Pri každom provideri klikni `Test` a potvrď, že je dostupný.
3. V bloku `Preferred voice provider (STT/TTS)` nastav prioritu:
   - `Auto` (odporúčané): STT `Grok -> Deepgram -> OpenAI`, TTS `Grok -> ElevenLabs -> OpenAI`
   - explicitný provider: vynúti prvú voľbu
4. Ulož preferencie tlačidlom `Save voice preferences`.
5. Over funkčnosť v Ballroom:
   - voice vstup sa prepíše na serveri,
   - Orchestrator odpoveď príde ako text + serverové audio.

Tip:
- Ak máš oba providery, používaj `Auto` pre najvyššiu odolnosť.
- Ak testuješ kvalitu/latenciu jedného providera, dočasne ho nastav explicitne.

### 8.2 EN - Configure STT/TTS providers in-app

Voice setup is available in `Settings -> AI + Voice keys`.

1. Store API keys you want to use:
   - STT: `Grok` or `Deepgram` or `OpenAI`
   - TTS: `Grok` or `ElevenLabs` or `OpenAI`
2. Run `Test` per provider to confirm connectivity.
3. In `Preferred voice provider (STT/TTS)`, choose priority:
   - `Auto` (recommended): STT `Grok -> Deepgram -> OpenAI`, TTS `Grok -> ElevenLabs -> OpenAI`
   - explicit provider: forces first choice
4. Save with `Save voice preferences`.
5. Verify in Ballroom:
   - voice input is transcribed server-side,
   - Orchestrator responses arrive as text + server-generated audio.

Tips:
- If both providers are configured, keep `Auto` for maximum resilience.
- Switch to an explicit provider temporarily when validating latency/quality.

### 8.3 SK/EN - Advanced voice tuning (VAD + Silence + Profile)

V tom istom paneli je dostupná sekcia advanced nastavení:

- `VAD threshold`: citlivosť zachytenia reči (nižšia hodnota = zachytí aj tichší hlas, vyššia = menej šumu).
- `Silence duration (ms)`: koľko ticha musí uplynúť, aby sa veta odoslala na server.
- `Voice profile / Voice tone / Voice language`: výstupný hlas pre serverový TTS (najmä pri Grok TTS).

Praktické presets:

- `Fast response`: `Response mode = Fast`, `Silence duration = 400-600`, `VAD threshold = 0.55-0.70`.
- `Balanced`: `Response mode = Balanced`, `Silence duration = 650-900`, `VAD threshold = 0.65-0.80`.
- `Noisy room`: `Response mode = Balanced`, `Silence duration = 900-1300`, `VAD threshold = 0.80-0.90`.

### 8.4 SK/EN - Lean Ballroom chat features (fast + low-overhead)

- Quick templates priamo v Ballroom compose lište: `Brainstorm`, `Code review`, `Daily sync`.
- Cielenie swarm odpovede cez mention: `@Orchestrator @Scout ...`.
- Voice panel zobrazuje:
  - capture duration,
  - orientačný cost estimate,
  - warning pre dlhé voice relácie,
  - hard cap (auto-stop) pre jednu voice session.

Tip: Pre najnižší load drž voice krátky (push-to-talk) a dlhšie úlohy rieš textom s template promptmi.
