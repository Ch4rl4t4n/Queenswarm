# Social Intel Swarm — setup (YouTube + X → HiveMind)

Automatický scrape kanálov a X účtov, ingest do Knowledge/HiveMind, denný delta tick, evaluator routine.

---

## Čo už beží v kóde (deploynuté)

| Komponent | Popis |
|-----------|--------|
| `social_intel_scraper` | YouTube playlistItems + X timeline API |
| `intel_source_cursors` | watermark per kanál/účet (delta scrape) |
| Celery `hive.social_intel_daily_tick` | default **07:30 UTC** denne |
| `POST /foragers/{id}/scrape` | manuálny backfill/delta + evaluator routine |
| `POST /foragers/{id}/sources` | pridať kanály/účty (aj z Queen promptu) |
| Skill `social-intel-evaluator` | tech + business scoring → HiveMind |

---

## Čo musíš urobiť TY (operátor)

### 1. API kľúče a OAuth (jednorazovo)

```bash
./scripts/operator-social-intel-prep.sh
```

| Položka | Kde |
|---------|-----|
| **YOUTUBE_API_KEY** | Google Cloud → enable YouTube Data API v3 → `.env.prod` |
| **X OAuth** | `.env.prod.oauth` + Integrations → Hub → **Connect** pri `twitter_api_v2` |
| **Redeploy** | po zmene env: `docker compose … up -d --build backend worker` |

> X API musí mať **Read** prístup k cudzím verejným timeline (Basic/Elevated podľa tieru). Bez toho X scrape vráti prázdne výsledky.

### 2. Foragery (automaticky alebo UI)

**Automaticky (odporúčané):**

```bash
./scripts/operator-social-intel-provision.sh
# alebo len prep + provision:
INSTALL=1 ./scripts/operator-social-intel-prep.sh
```

Vytvorí **YouTube Intel** + **X Intel** so starter kanálmi, pridá harness block do curated memory, spustí prvý scrape.

**Manuálne (UI):** Foragers → New:

**A) YouTube Intel**
- Source: **YouTube**
- Channels: jeden handle/URL na riadok (`@mkbhd`, `UC…`)
- Schedule: enabled, cron `0 7 * * *` (alebo nechaj beat 07:30 UTC)
- Filter tags: `intel`, `youtube`, `hivemind-candidate`
- Prompt template: použi skill `social-intel-evaluator` — zhrni, skóruj, ulož len keep/follow-up

**B) X Intel**
- Source: **X (Twitter)**
- Accounts: `@handle` alebo URL, jeden na riadok
- Rovnaký schedule + tags (`x`, `social-intel`)

### 3. Backfill (historický obsah)

Po vytvorení foragerov spusti **raz** manuálny scrape:

- UI: Foragers → **Trigger** (alebo Scrape ak je v UI)
- API:
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  https://queenswarm.love/api/v1/foragers/{FORAGER_ID}/scrape
```

Prvý beh stiahne až **50 položiek** na kanál/účet (`backfill_limit` v source_config).

### 4. Pridávanie kanálov cez prompt (Queen / API)

Keď napíšeš v chate „pridaj YouTube @newchannel“:

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"platform":"youtube","sources":["@newchannel"]}' \
  https://queenswarm.love/api/v1/foragers/{YOUTUBE_FORAGER_ID}/sources
```

Pre X: `"platform":"x"`, `"sources":["@handle"]`

*(Queen môže volať toto cez MCP/API keď máš workflow — inak dočasne API/curl.)*

### 5. Evaluator swarm (odporúčaný prompt)

V **Settings → AI · harness** pridaj:

```
Social intel: po každom scrape spusti researcher+critic s skill social-intel-evaluator.
Tech fit ≥3 alebo business ≥3 → HiveMind insight s tagom hivemind-candidate.
```

Forager routine automaticky spustí supervisor session s rolami **researcher + critic** po ingest.

### 6. Overenie

- **Knowledge** — nové riadky `source_type: forager:youtube` / `forager:twitter`
- **HiveMind search** — tag `social-intel`
- Logs: `social_intel.daily_tick`, `social_intel.forager_run_complete`

---

## Limity a škálovanie (100 kanálov)

| Riziko | Riešenie |
|--------|----------|
| YouTube API quota | batch po 20 kanáloch; zvýš quota v Google Cloud |
| X rate limits | Basic tier limit; zváž Apify connector pre heavy load |
| LLM cost evaluator | routine beží len keď `ingested > 0` |

---

## Súvisiace

- [`OPERATOR_FREE_INTEL_SETUP.md`](OPERATOR_FREE_INTEL_SETUP.md)
- [`OPERATOR_X_OAUTH_SETUP.md`](OPERATOR_X_OAUTH_SETUP.md)
- `scripts/operator-social-intel-prep.sh`
- `scripts/operator-social-intel-provision.sh`
