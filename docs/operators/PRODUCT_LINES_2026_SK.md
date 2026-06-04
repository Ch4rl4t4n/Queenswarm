# Product lines — 5 nápadov na predaj (2026–2028)

Strategický dokument pre Queenswarm. Vyber **2–3** na implementáciu po prvom Gumroad launch.

---

## Aktuálne jadro (už v appke)

| Produkt | Popis | Predaj |
|---------|--------|--------|
| **Verified Niche Harness (Skill)** | SKILL + HARNESS + EVAL + TOOLS | Gumroad + GitHub teaser |
| **Content Pack Harness** | Social/content packs, rovnaký eval lane | Gumroad |
| **MCP Ops** | Integrácia toolov pre harness | Súčasť SaaS / bundle |

---

## 5 nových produktových línií (kandidáti)

### 1. MCP Connector Starter Kits

**Čo:** Balíček pre jeden use-case — hotový MCP server config + SKILL + eval + test script (napr. „Competitor intel MCP kit“).

**Pre koho:** Solo founderi, agentúry používajúce Cursor/Claude Desktop.

**Prečo prežije:** MCP je štandard; ľudia nechcú skladať connector + context + eval od nuly.

**Cena:** €39–€99 · **Náročnosť implementácie:** stredná (Factory + Integrations export).

**Fit s appkou:** 9/10 — priamo MCP Ops + TOOLS.json.

---

### 2. Eval-as-a-Service Reports (one-shot)

**Čo:** Buyer nahraje svoj workflow/SKILL → Queenswarm spustí critic + simulate → PDF/MD **EVAL_REPORT** s PASS/FAIL a fix listom.

**Pre koho:** Tímy pred publikovaním agent workflow na produkciu.

**Prečo prežije:** Eval discipline je to, čo Karpathy hovorí že zostane; menej ľudí vie robiť kvalitné evals.

**Cena:** €19–€49 per report · **Náročnosť:** stredná (nový API endpoint + Gumroad product).

**Fit s appkou:** 10/10 — už máte quality gate + sandbox.

---

### 3. Harness Migration Pack (framework → Queenswarm/Cursor)

**Čo:** „Presuň sa z CrewAI/AutoGen na orchestrátor + MCP“ — niche-specific migračný playbook + SKILL + checklist.

**Pre koho:** Tímy s legacy agent kódom (presne mŕtvy hype z postu).

**Prečo prežije:** Veľa ľudí má mŕtvy kód a nevie kam ísť.

**Cena:** €49–€149 · **Náročnosť:** nízka (content + Factory, minimum kódu).

**Fit s appkou:** 8/10 — positioning proti mŕtvemu hype.

---

### 4. Vertical Hive-in-a-Box (tenant template)

**Čo:** Predkonfigurovaný tenant: curated memory + 3 verified recipes + 1 hero harness pre jednu vertikálu (napr. „Indie newsletter operator hive“).

**Pre koho:** Operátori chcúci hotový harness bez stavania od nula.

**Prečo prežije:** Context engineering + memory = dlhodobá hodnota.

**Cena:** €99–€299 one-time alebo €29/mo maintenance · **Náročnosť:** vysoká (seed scripts + import flow).

**Fit s appkou:** 9/10 — tenant settings + recipes + skills.

---

### 5. Operator Runbooks (Celery-safe automation recipes)

**Čo:** Predajné **runbooky** — nie agent, ale „keď X, spusti tento 5-krokový supervised session“ s eval gates (incident triage, weekly SEO audit, competitor digest).

**Pre koho:** Solo ops, malé SaaS, konzultanti.

**Prečo prežije:** Orchestrator-subagent + human-in-the-loop > autonómny agent.

**Cena:** €29–€79 per runbook · **Náročnosť:** stredná (Recipe Library export + Schedule routine).

**Fit s appkou:** 10/10 — recipes + supervisor sessions.

---

## Odporúčaný výber TOP 3 (na diskusiu)

| Priorita | Produkt | Prečo teraz |
|----------|---------|-------------|
| **#1** | Eval-as-a-Service Reports | Rýchly cash, minimálny nový UI, dôkaz eval hodnoty |
| **#2** | MCP Connector Starter Kits | Align s MCP štandardom, upsell k existujúcim harness packom |
| **#3** | Operator Runbooks | Prirodzené pokračovanie Skill Factory → Recipe schedule |

**Odložiť:** Migration Pack (marketing/content), Hive-in-a-Box (až keď import flow existuje).

---

## Čo sme vyradili / zmrazili v UI

- In-app Recipe Marketplace beta (panel skrytý)
- Trading, E-commerce, Browser automation moduly (frozen)
- Micro-SaaS factory + Media agency (Content Factory → len Pack factory)
- Volume factory messaging (cap 5 sellable/mesiac namiesto 50 draftov)

---

*Posledná aktualizácia: 2026-06 — Export 2.0 + Apps & Tools core/frozen tier.*
