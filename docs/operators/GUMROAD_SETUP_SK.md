# Gumroad — návod pre operátora (SK)

Tento dokument vysvetľuje, **čo potrebuješ ty** vs. **čo robí Queenswarm**, a čo **NIE JE** potrebné na prvý predaj.

---

## Rýchla odpoveď

| Otázka | Odpoveď |
|--------|---------|
| Potrebujem vlastnú webstránku? | **Nie** na prvý launch. Gumroad ti dá profil + URL produktu (`username.gumroad.com/l/...`). |
| Potrebujem registrovanú firmu / značku? | **Nie** na začiatok. Môžeš predávať ako fyzická osoba. DPH / živnosť riešiš neskôr pri väčšom obrate (EÚ). |
| Potrebujem OAuth „Application“ (Redirect URI)? | **Nie** pre Queenswarm. To je pre tretie strany, ktoré sa prihlasujú cez Gumroad účet používateľa. |
| Potrebujem access token? | **Voliteľné.** Bez tokenu nahraješ `.tar.gz` ručne. S tokenom appka vytvorí draft cez API. |
| Potrebujem GitHub PAT? | **Voliteľné** — len ak chceš automatické teaser repozitáre (Integrations). |

---

## Dve cesty na Gumroad

### Cesta A — Manuálny upload (odporúčané na prvý deň)

**Nepotrebuješ:** token, web, OAuth app, firmu.

1. Vytvor **Gumroad seller** účet na [gumroad.com](https://gumroad.com) (email + payout metóda neskôr).
2. V Queenswarm: **Apps & Tools → Skill Factory → Launch** — stiahni **Download pack** pre 1–3 hero produkty.
   - Na serveri sú aj hotové balíčky: `exports/gumroad-upload/<slug>.tar.gz`
   - Ku každému skillu existuje `LISTING.md` s popisom, cenou, tagmi.
3. V Gumroad: **Products → New product**
   - Typ: **Digital product**
   - Názov + popis skopíruj z `LISTING.md`
   - Cena: odporúčaná v Library / opportunity (napr. €19–€49)
   - Súbor: nahraj `.tar.gz` z kroku 2
   - Cover: 1 screenshot (môže byť hrubý — dashboard, README, ukážka SKILL.md)
4. Publikuj produkt. Zdieľaj link na X / Product Hunt / Reddit.

**Tvoja Gumroad stránka = tvoja „predajná webstránka“** na začiatok.

### Cesta B — API token (automatické drafty z appky)

**Potrebuješ:** len Gumroad seller účet + **Personal Access Token** (nie OAuth Application).

1. Prihlás sa na Gumroad ako predajca.
2. Choď na **Settings → Advanced** (nie sekciu „Applications“ s Redirect URI).
3. Nájdi **Generate access token** / **API access** pre **vlastný** účet.
4. Skopíruj token do Queenswarm:
   - **Integrations → Hub → `gumroad_rest`**, alebo
   - env `SKILL_FACTORY_GUMROAD_ACCESS_TOKEN` + `SKILL_FACTORY_GUMROAD_LISTING_ENABLED=true`
5. V **Skill Factory → Library / Launch** tlačidlo **Gumroad draft** vytvorí produkt cez API. Ty dokončíš cover + publish v Gumroad UI.

---

## Čo je na screenshote „Applications“ (OAuth)

Formulár s **Application name**, **Redirect URI**, **Upload icon** slúži pre:

- Aplikácie, kde sa **iní používatelia** prihlasujú cez Gumroad (OAuth 2.0).
- Potrebuješ verejnú callback URL (`https://queenswarm.love/...`).

Queenswarm **nepoužíva** tento flow. Používa **seller API token** pre tvoj vlastný obchod — rovnaký princíp ako „API key pre môj účet“.

---

## GitHub PAT (voliteľné)

Pre **teaser repozitáre** (verejný README + ukážka, plný pack na Gumroad):

1. GitHub → **Settings → Developer settings → Personal access tokens**
2. Vytvor token so scope **`repo`** (classic) alebo fine-grained s prístupom k repozitárom.
3. Queenswarm → **Integrations** (GitHub connector) alebo env pre skill factory export.

Bez PAT stiahneš pack ručne a môžeš repo vytvoriť sám.

---

## Hero niky (3 produkty na launch)

Default seedy v Skill Factory Settings:

- newsletter growth loop
- crypto / trading workflow (ak chceš)
- SEO content pipeline

Potvrď alebo uprav v **Skill Factory → Settings → Niche seeds**. Launch tab ukáže koľko skillov je **sellable** (kvalitný SKILL.md, nie generický draft).

---

## Právne / DPH (neskôr, nie blocker)

- **Gumroad (US)** spracuje platby; ty dostaneš payout.
- **EÚ / SK:** pri predaji do EÚ môže nastať DPH podľa pravidiel Gumroad + tvojho statusu. Pri prvých €100–€500 to často riešiš až keď vidíš trakciu.
- Alternatíva pre EÚ merchant-of-record: Lemon Squeezy (Phase 2 v pláne).

---

## Checklist — minimum od teba

- [ ] Gumroad seller účet
- [ ] 1–3 hero produkty vybrané v **Launch** tab
- [ ] 1–3 screenshoty (hrubé OK)
- [ ] Manuálny upload **alebo** access token pre API draft
- [ ] (Voliteľne) GitHub PAT pre teaser repos
- [ ] (Voliteľne) Potvrdené 3 niche seeds v Settings

Všetko ostatné (research, build, export, LISTING.md, `.tar.gz`) robí factory pipeline.

---

## Kde v appke

| Akcia | Cesta |
|-------|--------|
| Launch queue | Apps & Tools → Skill Factory → **Launch** |
| Stiahnuť pack | Launch / Library → **Download GitHub pack** |
| Gumroad draft (API) | Library → **Gumroad draft** (ak token) |
| Token / integrácia | Settings / Integrations → `gumroad_rest` |
| Operator skripty | `./scripts/factory-first-revenue-bootstrap.sh` |

---

*Posledná aktualizácia: 2026-05 — Fáza 1 Launch queue + sellable tier.*
