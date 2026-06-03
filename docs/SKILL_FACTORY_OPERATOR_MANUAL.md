# Skill Factory — Operator Manual

Kompletný návod na výrobu, nasadenie a predaj AI skills cez Queenswarm Skill Factory.

**Cesta v apke:** Apps & Tools → [Skill Factory](/apps-tools/skill-factory)  
**Filozofia:** Apka = výrobná linka. Predaj = GitHub / Gumroad mimo apky. Žiadny in-app marketplace.

---

## 0. Architektúra (čo sa deje pod kapotou)

```
Research (HiveMind + Skill Market Intel)
    ↓ ranked opportunities
Build (supervisor session — researcher → coder → critic)
    ↓ verified_skill_forge proposal
Approve (operátor)
    ↓ tenant_skills + Recipe Library
Library + Export (SKILL.md + README + LISTING)
    ↓
Runtime (SkillLibrary: 33 builtin + tenant overlay)
    ↓
Agents / Kanban / New task (skill picker)
```

---

## 1. Jednorazová príprava

| Krok | Kde | Prečo |
|------|-----|-------|
| LLM keys | Settings → AI · LLM keys | Factory session volá viacero bees |
| Auto-approve | Agents → Sessions | Solo režim — neblokovať každý micro-step |
| 2FA + security | Settings → Security | Operátorský prístup |
| Foragers (voliteľné) | Foragers | Lepšie research scores v HiveMind |
| Costs review | Settings → costs | Factory = viac LLM tokenov |

**Env (operátor nemusí meniť):** `SKILL_FACTORY_ENABLED=true`, research cron pondelok 08:00 UTC.

---

## 2. Nastavenie factory (Settings tab)

### Niche seeds
Pridaj 3–8 konkrétnych tém. Príklady:
- `newsletter growth automation`
- `SEO blog pipeline for indie hackers`
- `Cursor agent skills for dev teams`
- `lead gen outreach simulate-first`

Prázdne seeds → systém použije 8 default niches.

### Auto-build
| Nastavenie | Odporúčanie |
|------------|-------------|
| Auto-build | **OFF** prvý mesiac |
| Min score | 0.72 – 0.78 |
| Max builds/week | 2 – 3 |
| Research cron | ON |

### Externý intel (voliteľné)
| Nastavenie | Kedy zapnúť |
|------------|-------------|
| Apify deep scrape | Máš Apify connector — doplní Google SERP do Knowledge |
| Monid listing signals | Máš Monid connector — demand hook pri research |
| Monid listing preview on approve | Máš Monid connector — pri approve doplní `listing_preview` hook do exportu |
| Monid video preview on approve | Preview ON + Monid + env flag — Monid `run` pre video URL v LISTING.md |

Vyžaduje Tavily/Serper keys v Settings → Integrations (research live search).

### Hint pri ukladaní
Po každej zmene klikni **Save policy**. Bez uloženia cron nepoužije nové seeds.

---

## 3. Research tab

### Run research now
1. HiveMind semantic search pre každý niche
2. Skill Market Intel — demand keywords (cursor, skill, n8n, automation…)
3. Scoring: demand × buildability × (1 − competition)
4. Výstup: `SkillOpportunity` rows v DB

### Ako čítať kartu
| Pole | Význam |
|------|--------|
| Composite % | Celkové skóre — ≥72% = auto-build eligible |
| €9 / €19 / €29 | Cenový anchor pre externý predaj |
| Rationale | HiveMind hits, intel signály, podobné queued skills |

### Akcie
- **Build skill** — spustí factory session
- **Dismiss** — skryje niche z fronty

**Hint:** Dismiss generic niche („AI agent skill“). Buduj tam, kde máš domain know-how.

---

## 4. Build & Queue

Po **Build skill**:
1. Opportunity → status `building`
2. Vytvorí sa supervisor session s factory goal (PRODUCT_MISSION template)
3. Queue tab — link na Sessions + stav buildu

**Factory goal obsahuje:** niche, price anchor, skill-authoring-template, verify guardrails, quality gate pred forge.

**Hint:** Jeden build naraz. Paralelné runy = vyšší cost + nižšia kvalita.

---

## 5. Sledovanie session (Agents → Sessions)

| Fáza | Bee | Výstup |
|------|-----|--------|
| Spec | researcher | niche brief, persona, competitors |
| Author | coder | SKILL.md draft |
| Package | coder | README, LISTING, meta |
| Verify | critic | APPROVE / REJECT |

**Statusy:**
- `running` — počkaj
- `needs_input` — odpovedz stručne v session
- `completed` — choď na Suggestions

**Hint:** Info report ukáže resolved skills. Pri REJECT — upresni goal, nová session (nie retry raw).

---

## 6. Schválenie forge (Queue tab — inline)

Primárna cesta: **Apps & Tools → Skill Factory → Queue** — pri hotovom builde klikni **Approve skill**.

Alternatíva: Agents → Suggestions → `verified_skill_forge`.

- **Approve** → tenant skill v DB + recipe v Recipe Library
- **Reject** → nič sa neuloží do Library

Po approve (ak je zapnuté *Monid listing preview on approve*):
- Monid discover doplní `one_line_hook` do opportunity `source_refs.listing_preview`
- Export bundle použije Gumroad-ready LISTING.md s týmto hookom

Po approve vždy:
- Skill sa objaví v **Library** tab
- Skill picker ukáže chip s badge `factory`
- SkillLibrary overlay pri ďalších sessions

**Hint:** Schváľ len keď SKILL.md obsahuje konkrétne kroky, guardrails a evaluation criteria.

---

## 7. Export (Library tab)

**Download GitHub pack** obsahuje:
- `SKILL.md` — runtime skill pre Cursor/Claude harness
- `README.md` — inštalácia a usage
- `LISTING.md` — **Gumroad-ready** copy (hook, persona, price tiers, video block, FAQ, launch checklist)
- `meta.json` — slug, keywords, version

LISTING.md sa generuje zo Skill Factory kontextu (niche, price anchor, Monid hook ak bol pri approve).

### GitHub (odporúčaný flow)
1. Stiahni zip **alebo** klikni **Push GitHub PR** (Library tab) keď je `github_rest` connector + env target nakonfigurovaný
2. Vytvor repo `your-skill-pack-name` (ak nepoužívaš auto PR)
3. Skopíruj súbory, commit, push
4. Topics: `cursor-skill`, `agent-skill`, `ai-automation`

**Auto PR env:** `SKILL_FACTORY_GITHUB_PR_ENABLED=true`, `SKILL_FACTORY_GITHUB_OWNER`, `SKILL_FACTORY_GITHUB_REPO`

### Gumroad (voliteľné — API draft + publish)
1. Nastav `SKILL_FACTORY_GUMROAD_LISTING_ENABLED=true` + `SKILL_FACTORY_GUMROAD_ACCESS_TOKEN` (alebo connector `gumroad_rest`)
2. Library → **Gumroad draft** — vytvorí draft produkt z LISTING.md (ZIP bundle + cover ak sú zapnuté)
3. Library → **Gumroad publish** — `PUT /products/:id/enable` (draft → live). Ak chýba draft, tlačidlo vytvorí draft aj publish naraz (`create_if_missing`).
4. Env pre publish: `SKILL_FACTORY_GUMROAD_PUBLISH_ENABLED=true` (default off — bezpečný rollout)

### Gumroad (manuálne)
1. Použi LISTING.md z GitHub packu ako popis
2. Cena podľa suggested price z research
3. Screenshot z Queenswarm verify report ako social proof

**Hint:** Auto GitHub push zatiaľ nie je — manuálny upload.

---

## 8. Použitie skillov v hive

| Miesto | Správanie |
|--------|-----------|
| Agents → Sessions | Skills override chips — prázdne = auto |
| Mission Kanban | Chips pri triage/dispatch |
| Tasks → New task | Chips v execution_payload |
| Session report | Read-only resolved skills by role |

**Hint:** Pripni factory slug keď chceš vynútiť skill. Inak Pattern Router + SkillLibrary auto-match.

---

## 9. Stratégické odporúčania

### Primary: interné skills
Najväčší ROI = skill, ktorý denne používaš v sessions. Externý predaj = bonus z top 10–20 % outputu.

### Secondary: cherry-pick predaj
1–2 skills / mesiac na GitHub/Gumroad. Generic packs nepredávaj.

### Čomu sa vyhnúť
- In-app marketplace / UGC / premium checkout (vypnuté zámerne)
- Auto-build bez overeného prvého cyklu
- Schvaľovanie raw LLM output bez simulate
- Paralelné factory runy (>3/týždeň)

### Realistický príjem (solo, externý predaj)
| Scenár | €/mesiac |
|--------|----------|
| 1 hit skill + marketing | 200 – 800 |
| 4 stredné skills + SEO | 500 – 2000 |
| Factory bez distribúcie | ~0 (len LLM cost) |

---

## 10. Čo je hotové vs. čo ešte treba

### Hotové (systém)
- [x] Research + scoring + cron + weekly build cap
- [x] External intel (Tavily/Serper) + voliteľný Apify deep scrape
- [x] Monid listing signals pri research
- [x] Quality gate (critic APPROVE + SKILL.md validator) pred forge
- [x] Build session + verify loop (PRODUCT_MISSION)
- [x] Queue inline approve + forge → tenant registry + recipe
- [x] Monid listing preview hook pri approve (voliteľné)
- [x] Monid video preview URL pri approve (voliteľné, Execution Studio)
- [x] Auto GitHub PR z Library exportu (voliteľné, github_rest connector)
- [x] Gumroad draft listing API z Library (voliteľné)
- [x] Gumroad publish API (draft → live) z Library (voliteľné)
- [x] Gumroad-ready LISTING.md v GitHub export bundle
- [x] Skill picker (Sessions, Kanban, New task)
- [x] Marketplace skrytý v solo režime

### Tvoj operátorský krok
- [ ] Prvý celý cyklus: Build → Approve → Export
- [ ] Niche seeds prispôsobené tvojmu biznisu
- [ ] LLM budget skontrolovaný pred auto-build
- [ ] (Voliteľne) Foragers krmia HiveMind

### Plánované v produkte
- [ ] Stripe / checkout integrácia (zámerne mimo scope — predaj cez Gumroad)

---

## 11. Riešenie problémov

| Problém | Riešenie |
|---------|----------|
| Skill Factory unavailable | Skontroluj `skill_factory` feature flag + `SKILL_FACTORY_ENABLED` |
| Research 0 opportunities | Všetky niches už pending — dismiss alebo počkaj na nový týždeň |
| Build failed | Sessions → error detail; skontroluj LLM keys |
| Library prázdna | Chýba approve verified_skill_forge |
| Skills nevidí agent | Approve forge; refresh session s pinned slug |
| Nízke research scores | Spusti Foragers / Ingest URL pre HiveMind |

---

## 12. Súvisiace docs

- `docs/OPERATOR_CANONICAL_WORKFLOW.md` — primárna cesta Agents → Sessions
- `/manual#skill-hot-tier` — builtin recipe hot tier
- `/manual#automation-ladder` — L3 routines z verified recipes

---

*Posledná aktualizácia: Gumroad publish API (draft → live) + Library export tlačidlá.*
