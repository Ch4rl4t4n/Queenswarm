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
2. Vytvorí sa supervisor session s factory goal
3. Queue tab — link na Sessions

**Factory goal obsahuje:** niche, price anchor, skill-authoring-template, verify guardrails.

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

## 6. Schválenie forge (Agents → Suggestions)

Hľadaj `verified_skill_forge`:
- **Approve** → tenant skill v DB + recipe v Recipe Library
- **Reject** → nič sa neuloží do Library

Po approve:
- Skill sa objaví v **Library** tab
- Skill picker ukáže chip s badge `factory`
- SkillLibrary overlay pri ďalších sessions

**Hint:** Schváľ len keď SKILL.md obsahuje konkrétne kroky, guardrails a evaluation criteria.

---

## 7. Export (Library tab)

**Download GitHub pack** obsahuje:
- `SKILL.md` — runtime skill pre Cursor/Claude harness
- `README.md` — inštalácia a usage
- `LISTING.md` — copy pre Gumroad/Product Hunt
- `meta.json` — slug, keywords, version

### GitHub (odporúčaný flow)
1. Stiahni zip
2. Vytvor repo `your-skill-pack-name`
3. Skopíruj súbory, commit, push
4. Topics: `cursor-skill`, `agent-skill`, `ai-automation`

### Gumroad (voliteľné)
1. Použi LISTING.md ako popis
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
- [x] Research + scoring + cron
- [x] Build session + verify loop
- [x] Forge approve → tenant registry + recipe
- [x] GitHub export bundle
- [x] Skill picker (Sessions, Kanban, New task)
- [x] Marketplace skrytý v solo režime

### Tvoj operátorský krok
- [ ] Prvý celý cyklus: Build → Approve → Export
- [ ] Niche seeds prispôsobené tvojmu biznisu
- [ ] LLM budget skontrolovaný pred auto-build
- [ ] (Voliteľne) Foragers krmia HiveMind

### Plánované v produkte
- [ ] Live GitHub/Gumroad market scrapers
- [ ] Auto GitHub PR z exportu
- [ ] Gumroad API listing

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

*Posledná aktualizácia: Skill Factory fázy A–E + Skill Market Intel + operator Guide tab.*
