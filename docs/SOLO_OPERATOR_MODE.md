# Queenswarm Solo operator mode — Queenswarm

Režim pre **jediného operátora** (ty): plný admin prístup, **všetky revenue nástroje** (marketplace, UGC, Factory, trading), žiadni hostia.

## Rýchly štart — `SOLO_MODE_ENABLED` (odporúčané)

```bash
# Aplikuje .env.solo.example → .env.prod a redeployne backend + frontend
chmod +x ./scripts/apply-solo-mode.sh
./scripts/apply-solo-mode.sh

# Zapne revenue env + platform matrix (marketplace, Factory, …)
./scripts/operator-solo-revenue-full.sh
```

Jeden prepínač **`SOLO_MODE_ENABLED=true`** v `.env.prod`:
- skryje len **multi-tenant B2B** (team RBAC, enterprise workspace, accounts admin)
- **billing, marketplace, UGC, gamifikácia, Factory** zostávajú zapnuté pre admina
- `/auth/me` vráti `solo_mode: true` + upravenú `platform_features` mapu

**Späť na multi-tenant commercial:** `SOLO_MODE_ENABLED=false`, redeploy.

**My 3 Bees + Brain Pack:** návod `docs/SOLO_OPERATOR_TRIO_GUIDE.md` · Instagram/publish koncept `docs/PRODUCTION_AUTOMATION_PHASES.md`

**Kanonický operátorský workflow (P0):** `docs/OPERATOR_CANONICAL_WORKFLOW.md` · UI `/manual#canonical-workflow`

Voliteľné moduly (foragers, simulations, …) sú v solo **default ON** pre admina; vypneš v **Settings → Platform → stĺpec Prostredie**.

---

## Rýchly štart (15 min) — manuálny lockdown

```bash
# 1. Audit účtov + prostredí
./scripts/operator-solo-lockdown.sh

# 2. Deaktivuj test/extra účty (nechá admin@queenswarm.love)
APPLY=1 OPERATOR_EMAIL=admin@queenswarm.love ./scripts/operator-solo-lockdown.sh

# 3. Obmedz prístup na tvoju IP (HTTPS)
# Zisti IP: curl -4 ifconfig.me
OPERATOR_IP=TVA.IP.ADRESA ./scripts/operator-solo-nginx-allowlist.sh enable

# 4. Redeploy (nginx include mount)
ENV_FILE=.env.prod ./scripts/deploy-prod.sh

# 5. V UI: Settings → Platform → stĺpec „Prostredie“ — vypni nepotrebné (nižšie)
```

---

## Prístup — len ty

| Vrstva | Čo robí | Stav |
|--------|---------|------|
| **Registrácia** | Neexistuje — účty len cez bootstrap/admin | ✅ už tak |
| **Extra účty** | `rbac-smoke@…` a pod. → deaktivovať | `./scripts/operator-solo-lockdown.sh` |
| **2FA** | TOTP pri logine; znova po 24 h | `.env.prod`: `ENABLE_2FA=true`, `DASHBOARD_2FA_SESSION_MAX_HOURS=24` |
| **IP allowlist** | nginx `allow TVOJA_IP; deny all;` na :443 | `./scripts/operator-solo-nginx-allowlist.sh` (viac IP — pozri nižšie) |
| **M2M tokeny** | Vypnuté ak nenastavíš `HIVE_TOKEN_CLIENT_*` | odporúčané |

**Poznámka:** Po zapnutí IP allowlistu sa dostaneš na app len z tej IP (mobil = iná sieť → pridaj druhú IP alebo dočasne `disable`).

### IP allowlist + mobil / práca / notebook

Každá sieť má **inú verejnú IP** (domov, kancelária, mobilné dáta). Mobilná LTE IP sa navyše **mení** — nie vždy, ale často.

| Scenár | Odporúčanie |
|--------|-------------|
| Len doma na PC | IP allowlist stačí (1 IP) |
| Dom + práca + telefón | Pridaj **viac IP naraz** (oddelené čiarkou) alebo allowlist **nevypínaj** — 2FA ti stačí |
| Často meníš sieť | **Nepoužívaj** IP lock; nechaj vypnutý a spoliehaj sa na 2FA |

Viac IP naraz (skript to už podporuje):

```bash
# Zisti IP: curl -4 ifconfig.me  (na každej sieti raz)
OPERATOR_IP=203.0.113.10,198.51.100.2,2001:db8::1 ./scripts/operator-solo-nginx-allowlist.sh enable
```

Alternatíva: **VPN** s jednou fixnou výstupnou IP — v allowliste len tá VPN IP, všade inde sa pripájaš cez VPN.

**Prakticky pre teba:** Keď chceš appku vonku aj v práci na telefóne, **nechaj IP allowlist vypnutý** (ako teraz). 2FA + 24 h relácia sú dostatočné; IP by si musel priebežne dopĺňať pri každej novej sieti.

---

## Prostredia

| Prostredie | Odporúčanie |
|------------|-------------|
| **prod** (`queenswarm_prod`) | Nech beží |
| **stg** (`queenswarm_stg`) | Vypnúť — `docker compose -p queenswarm_stg down` |
| **dev** (`queenswarm`) | Vypnúť ak beží paralelne |

Lockdown skript to robí pri `APPLY=1`.

---

## Feature audit — čo vypnúť v Settings → Platform

Stĺpec **„Prostredie“** = globálny kill-switch (vypne pre všetkých).

### Nechaj ZAPNUTÉ (jádro + revenue pre teba)

| Feature | Prečo |
|---------|--------|
| `dashboard` | Hlavný cockpit |
| `swarms`, `agents`, `tasks`, `workflows` | Swarm + práca |
| `knowledge` | Hive Mind / vault |
| `integrations`, `connectors` | MCP / tools |
| `settings`, `llm_keys_settings`, `api_keys_settings` | Konfigurácia |
| `billing_settings` | Billing panel — checkout disabled |
| `skills_marketplace`, `ugc_content_engine` | Predaj skills + lead magnety |
| `skills_export_factory`, `product_mission` | Factory + product ship |
| `bee_gamification`, `leaderboard` | Pollen / verified leaderboard |
| `ai_harness_dashboard` | Harness / Maintainer |
| `pattern_explorer` | Pattern router prehľad |
| `costs`, `monitoring` | LLM náklady + health |
| `recipes` | Overené workflowy |
| `platform_features_admin` | Ty sám toggleuješ features |

### Vypni (solo — multi-tenant B2B)

| Feature | Prečo vypnúť |
|---------|--------------|
| `team_rbac` | Nepotrebuješ tím |
| `enterprise_workspace` | B2B white-label pre zákazníkov |
| `accounts_admin` | Multi-tenant správa účtov |

### Zapni podľa potreby

| Feature | Kedy |
|---------|------|
| `sharing_settings` | Zdieľanie workspace s partnerom |
| `design_system` | Dev showcase `/design-system` |
| `foragers` | Daily intelligence scan |
| `ballroom`, `dump_sleep`, `overnight_voice_report` | Voice / overnight pipeline |
| `auto_graphify`, `selective_recall` | Knowledge graph heavy |
| `self_extending_tool_marketplace` | One-click MCP install |
| `slack_harness_trainer` | Máš Slack webhook |
| `simulations`, `jobs` | Sandbox / batch joby |
| `sub_swarm_mind_ui` | Sub-swarm board |

---

## .env.prod — solo hardening

```bash
PRODUCTION_SECURITY_MODE=true
ENABLE_2FA=true
SECURITY_2FA_ADVANCED_ENABLED=true
RATE_LIMIT_ENABLED=true
RATE_LIMIT_USER_ENABLED=true
DEFAULT_TENANT_PLATFORM_MODE=internal

# Guest / M2M off
BALLROOM_GUEST_WS=false
HIVE_DASHBOARD_GUEST_WS=false
# HIVE_TOKEN_CLIENT_ID=     # nech prázdne
# HIVE_TOKEN_CLIENT_SECRET=

RECIPE_CATALOG_MUTATIONS_ENABLED=false
```

Overenie:

```bash
./scripts/validate-prod-env.sh
./scripts/audit-host-exposure.sh
```

---

## Externé kľúče — postupne dopĺňaj

| Kľúč / integrácia | Kde nastaviť | Priorita |
|-------------------|--------------|----------|
| **LLM (Grok / Claude / GPT)** | Settings → LLM keys | P0 — bez toho swarm nebeží |
| **VC OAuth (Notion/Gmail/GitHub)** | `.env.prod.oauth` + Execution Studio Connect | P0 — 70→100 % readiness |
| **GitHub webhook** | `.env.prod` + GitHub repo | P1 — Queen Maintainer auto |
| **Forager cron** | `FORAGER_INTELLIGENCE_LOOP_ENABLED=true` | P1 |
| **Slack alerts** | `SLACK_WEBHOOK_URL` | P2 |
| **Slack harness trainer** | `SLACK_HARNESS_TRAINER_*` | P2 |
| **Billing panel** | Settings → Billing | P1 — premium tiers and usage visibility |
| **Neo4j / Postgres** | už v `.env.prod` | hotové |
| **Connector vault** | `CONNECTOR_VAULT_FERNET_KEY` | hotové ak deploy prešiel |

Postup pre harness:

```bash
./scripts/operator-github-webhook-prep.sh
./scripts/operator-harness-env-prep.sh
ENV_FILE=.env.prod ./scripts/deploy-prod.sh
```

---

## Virtual Company solo — OAuth (Priority 1 pri readiness &lt; 100 %)

Simulate playbooks a swarms môžu byť hotové; **OAuth je posledný krok** na 100 % readiness.

| Krok | Príkaz / akcia |
|------|----------------|
| Status | `./scripts/operator-vc-status-report.sh` |
| All-in-one guide | `./scripts/operator-oauth-one-shot.sh` |
| Vendor URL | `./scripts/operator-oauth-open-vendors.sh` |
| Env súbor | `.env.prod.oauth` (gitignored overlay) |
| Init env | `./scripts/operator-oauth-env-init.sh` |
| Po doplnení kľúčov | `./scripts/operator-oauth-redeploy.sh` |
| Verify | `./scripts/operator-post-oauth-verify.sh` |
| UI Connect | https://queenswarm.love/integrations?tab=studio |

**Redirect URI** (Notion, Google, GitHub):

```text
https://queenswarm.love/api/auth/callback/oauth
```

**Env kľúče** v `.env.prod.oauth`:

- `OAUTH_NOTION_CLIENT_ID` / `OAUTH_NOTION_CLIENT_SECRET`
- `OAUTH_GOOGLE_CLIENT_ID` / `OAUTH_GOOGLE_CLIENT_SECRET`
- `OAUTH_GITHUB_CLIENT_ID` / `OAUTH_GITHUB_CLIENT_SECRET`

Po OAuth callback sa aktivujú connectory a solo Super Tool Routers automaticky.

**Alternatíva bez OAuth app (Notion + GitHub):** manuálne tokeny — Gmail stále potrebuje Google OAuth.

```bash
cp .env.prod.tokens.example .env.prod.tokens
# NOTION_INTEGRATION_TOKEN + GITHUB_PAT
APPLY=1 ./scripts/operator-vc-manual-tokens.sh
```

---

## Automatizácia „appka beží sama“

| Čo | Ako |
|----|-----|
| Queen Maintainer | GitHub webhook + `QUEEN_MAINTAINER_ENABLED=true` |
| Forager daily | `FORAGER_INTELLIGENCE_LOOP_ENABLED=true` |
| Alertmanager | `SLACK_WEBHOOK_URL` + `./scripts/alertmanager-smoke.sh` |
| Disk cleanup | `./scripts/install-daily-disk-cleanup-cron.sh` |
| **Ops automation (full)** | `APPLY=1 ./scripts/install-ops-automation-cron.sh` |
| DB backup + watchdog + SSL | included in ops automation installer |
| Security audit | mesačne `./scripts/audit-host-exposure.sh` |

---

## Čo NIE je potrebné pre solo mesiace

- Payment-vendor checkout go-live
- Hetzner — hotové
- Verejný marketing / UGC
- Viac tenantov / commercial demo
- CI deep_validation (manuálne keď treba)

---

## Skripty

| Skript | Účel |
|--------|------|
| `./scripts/operator-solo-lockdown.sh` | Audit účtov + env |
| `./scripts/operator-solo-nginx-allowlist.sh` | IP lock |
| `./scripts/operator-harness-env-prep.sh` | Harness env |
| `./scripts/operator-next.sh` | Ďalší krok (ak niečo zostane) |
| `./scripts/operator-oauth-one-shot.sh` | VC OAuth blocker — status + guide |
| `./scripts/operator-vc-status-report.sh` | VC readiness prehľad |
| `./scripts/operator-oauth-redeploy.sh` | Redeploy po `.env.prod.oauth` |
| `./scripts/compose-prod.sh` | Docker compose s oauth overlay |
