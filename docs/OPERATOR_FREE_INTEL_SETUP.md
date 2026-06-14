# Free intel stack — podrobný návod (operátor)

Nastavenie **bez Stripe / Shopify / GA4** — len zdroje na zber informácií.

**Redirect URI pre všetkých OAuth vendorov (vždy rovnaká):**

```
https://queenswarm.love/api/auth/callback/oauth
```

Overiť v termináli:

```bash
./scripts/operator-oauth-env-prep.sh
```

---

## Rýchly štart

```bash
# 1) Nainštaluj Calendar + Polymarket Gamma shells (+ auto-test Gamma)
TEST=1 INSTALL=1 ./scripts/operator-free-intel-prep.sh

# 2) Stav social OAuth
./scripts/operator-social-oauth-status.sh

# 3) Po úprave .env.prod.oauth vždy redeploy
REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh
./scripts/operator-post-oauth-verify.sh
```

UI: [Integrations → Hub](https://queenswarm.love/integrations?tab=hub)

---

## Čo už máš hotové (netreba znova)

| Zdroj | Stav | Úloha |
|-------|------|-------|
| Gmail | active | inbox, vlákna |
| Notion | active | knowledge |
| GitHub | active | repá, issues |
| Instagram | active | social |
| Telegram | active | bot / notifikácie |
| HiveMind + Forager | env ON | denný scan 6:00 · **P10 DG1–DG8** wizard + alerts → [`ROADMAP.md`](ROADMAP.md) Track I |
| LSP bridge | env ON | codebase intel |

---

## Krok 1 — Google Calendar (free OAuth)

**Na čo:** udalosti, plánovanie, morning brief, Execution Studio calendar lane.

### 1.1 Google Cloud Console

1. Otvor [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
2. Použi **ten istý projekt** ako pre Gmail (ak Gmail už funguje)
3. **APIs & Services → Library** → vyhľadaj **Google Calendar API** → **Enable**
4. OAuth client (Web application) — **nemusíš vytvárať nový**, ak už máš Gmail client:
   - Authorized redirect URI musí obsahovať:
     `https://queenswarm.love/api/auth/callback/oauth`
5. Skopíruj Client ID + Secret do `.env.prod.oauth` (ak ešte nie sú):

```bash
OAUTH_GOOGLE_CLIENT_ID=....apps.googleusercontent.com
OAUTH_GOOGLE_CLIENT_SECRET=GOCSPX-...
```

> Gmail a Calendar zdieľajú **rovnaké Google OAuth app credentials**, ale v UI sa pripájajú **samostatne** (iný scope).

### 1.2 Provision template v Queenswarm

```bash
INSTALL=1 ./scripts/operator-free-intel-prep.sh
```

Alebo v UI:

1. [Integrations → Hub → Templates](https://queenswarm.love/integrations?tab=hub&hubSection=templates)
2. Kategória **Calendar** (ak nie je v bubline, hľadaj v **Email/Calendar**)
3. Nájdi **Google Calendar** → **Configure** (voliteľne slug `google_calendar`) → **Provision**

### 1.3 OAuth Connect

1. [Integrations → Hub → OAuth](https://queenswarm.love/integrations?tab=hub&hubSection=oauth) (alebo OAuth rail hore na Hub stránke)
2. Nájdi kartu **Google Calendar** → **Connect**
3. Prihlás sa Google účtom → povol prístup ku kalendáru
4. Po redirecte by mal flash ukázať úspech

### 1.4 Overenie

1. Hub → **Roster** — riadok `google_calendar` → **Active**
2. Execution Studio → **Test connection** (ak je tlačidlo pri connectore)
3. Voliteľne API:

```bash
TOKEN=$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py)
curl -sk -H "Authorization: Bearer $TOKEN" \
  "https://queenswarm.love/api/v1/connectors/dynamic" | grep google_calendar
```

---

## Krok 2 — Facebook + X (Twitter) OAuth

**Na čo:** social listening, publish intel, forager gaps.  
**Poznámka:** ide o **OAuth connect**, nie o live post (live môžeš nechať vypnutý).

### 2.1 Env kľúče (`.env.prod.oauth`)

Meta (Instagram + Facebook):

```bash
OAUTH_META_CLIENT_ID=...
OAUTH_META_CLIENT_SECRET=...
```

X (Twitter):

```bash
OAUTH_X_CLIENT_ID=...
OAUTH_X_CLIENT_SECRET=...
```

Detailné vendor návody:

- Meta/IG: [`docs/OPERATOR_META_INSTAGRAM_OAUTH.md`](OPERATOR_META_INSTAGRAM_OAUTH.md)
- X: [`docs/OPERATOR_X_OAUTH_SETUP.md`](OPERATOR_X_OAUTH_SETUP.md)
- Všetci vendori: `./scripts/operator-oauth-register-guide.sh`

Po vyplnení:

```bash
REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh
./scripts/operator-post-oauth-verify.sh
```

### 2.2 Connectory (už máš nainštalované)

| Slug | Template | OAuth provider |
|------|----------|----------------|
| `facebook_graph` | Facebook Graph Pages | Meta |
| `twitter_api_v2` | X API v2 | X (PKCE) |

Ak chýbajú: Hub → **Templates** → kategória **Social** → Provision.

### 2.3 Connect v UI

1. [Integrations → Hub → OAuth](https://queenswarm.love/integrations?tab=hub&hubSection=oauth)
2. **Facebook · Meta Graph Pages** → **Connect**
   - Vyber Facebook Page prepojenú s účtom
3. **X (Twitter) · API v2** → **Connect**
   - OAuth 2.0 PKCE flow v prehliadači

### 2.4 Overenie

```bash
./scripts/operator-social-oauth-status.sh
```

Očakávaný výstup:

```
OK  facebook ... active=True (alebo credentials_ok)
OK  twitter ... active=True
```

Operator hub → **Social OAuth readiness** — `Connected: 2+` (Instagram už máš).

---

## Krok 3 — Polymarket Gamma (read-only, bez secretov)

**Na čo:** verejné trhy, eventy, research bees, forager market intel.  
**Auth:** `none` — **žiadny API kľúč**, len provision + test.

### 3.1 Provision

```bash
INSTALL=1 ./scripts/operator-free-intel-prep.sh
```

Alebo UI: Hub → **Templates** → kategória **Trading** → **Polymarket · Gamma (markets)** → **Provision**

Slug: `polymarket_gamma`  
Base URL: `https://gamma-api.polymarket.com`

### 3.2 Aktivácia (Test connection)

1. [Integrations → Hub → Roster](https://queenswarm.love/integrations?tab=hub&hubSection=roster)
2. Nájdi `polymarket_gamma`
3. Klikni **Test** (volá `POST /api/v1/connectors/dynamic/{id}/test`, nie `/ping`)
4. Po úspechu → status **Active**

Alebo z terminálu:

```bash
TEST=1 INSTALL=1 ./scripts/operator-free-intel-prep.sh
```

> **Poznámka:** `/connectors/{slug}/ping` vyžaduje vault credentials. Pre `auth_type=none` používaj **Test** v Rosteri alebo dynamic `/test` endpoint vyššie.

Bez secretov — ak test zlyhá, skontroluj outbound sieť z backendu (Gamma API musí byť dostupné).

### 3.3 Overenie (voliteľné)

```bash
curl -sS "https://gamma-api.polymarket.com/markets?limit=1" | head -c 200
```

V swarne: Research Bee / trading intel lane môže volať tools `markets_list`, `events_list`.

> **Neprepájaj** `polymarket_clob` — to je live trading, nie free intel.

---

## Krok 4 — Využiť to, čo už beží (bez nových pluginov)

| Čo | Kde | Frekvencia |
|----|-----|------------|
| Forager intelligence | Celery cron `FORAGER_INTELLIGENCE_CRON_HOUR=6` | denne |
| HiveMind ingest | Knowledge → HiveMind | priebežne |
| Research Bee | Apps / harness / URL paste | on-demand |
| LSP bridge | Agents / codebase search | on-demand |
| Ballroom dump | `/ballroom` upload | overnight |
| Trio cycle | Settings → Operator hub / Dnešný plán | ráno |

---

## Čo teraz **nedávať** (až keď bude aktuálne)

| Plugin | Prečo počkať |
|--------|--------------|
| Shopify / Stripe / GA4 | e-shop analytics |
| Venice MCP | media gen, nie zber |
| Apify | paid/free tier scraping — až pri competitor automate |
| TikTok | env ešte chýba |
| Polymarket CLOB | live trading |

---

## Aktuálny stav (prod snapshot)

| Connector | Stav | Čo treba od teba |
|-----------|------|------------------|
| `google_calendar` | nainštalovaný, neaktívny | OAuth **Connect** v Hub |
| `polymarket_gamma` | **aktívny** (test OK) | nič |
| `facebook_graph` | nainštalovaný, bez tokenu | OAuth **Connect** |
| `twitter_api_v2` | nainštalovaný, bez tokenu | OAuth **Connect** |
| Instagram | aktívny | hotové |

---

## Checklist po dokončení

- [ ] `google_calendar` — provisioned + OAuth Connect + **Active**
- [ ] `facebook_graph` — **Connect** (credentials OK)
- [ ] `twitter_api_v2` — **Connect** (credentials OK)
- [ ] `polymarket_gamma` — provisioned + **Test** → Active
- [ ] `./scripts/operator-social-oauth-status.sh` — aspoň 2 social kanály connected
- [ ] `./scripts/operator-free-intel-prep.sh` — všetky ✓ v rosteri

---

## Riešenie problémov

| Problém | Riešenie |
|---------|----------|
| OAuth „misconfigured vendor“ | `.env.prod.oauth` → `REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh` |
| Google Calendar 403 | Enable **Calendar API** v Google Cloud |
| Gmail funguje, Calendar nie | Samostatný **Connect** na `google_calendar` (iný scope) |
| Facebook Connect zlyhá | Meta app → Business, pridaj Instagram Graph + Facebook Login produkty |
| X Connect zlyhá | Callback URL presne `https://queenswarm.love/api/auth/callback/oauth`, Read+Write |
| Polymarket neaktívny | Roster → Test connection; auth_type = none |

---

## Súvisiace skripty

| Skript | Účel |
|--------|------|
| `scripts/operator-free-intel-prep.sh` | Calendar + Gamma shells + status |
| `scripts/operator-oauth-register-guide.sh` | Vendor registration text |
| `scripts/operator-oauth-redeploy.sh` | Načítať OAuth env do prod |
| `scripts/operator-social-oauth-status.sh` | Social OAuth probe |
| `scripts/audit-swarm-readiness-gate.sh` | Celkový readiness audit |
