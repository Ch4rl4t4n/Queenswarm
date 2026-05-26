# Publish lane → live — 15 min Meta OAuth (solo operátor)

Presný postup pre **queenswarm.love**. Secrets len v `.env.prod.oauth` — nikdy do git.

**Pred live vždy:** Publish Queue approve → Social **Simulate** → až potom `SOCIAL_PUBLISH_LIVE_ENABLED=true`.

---

## Rýchly one-shot (na hive hoste)

```bash
cd /root/Queenswarm

# 1) Priprav overlay + checklist
./scripts/operator-publish-live-rollout.sh

# 2) Po vyplnení Meta kľúčov v .env.prod.oauth:
REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh

# 3) UI: Marketplace → Install IG/FB → Hub → Connect

# 4) Simulate + live flip (automaticky overí gate):
RUN_SIMULATE=1 CONFIRM_LIVE=1 ./scripts/operator-publish-live-rollout.sh
```

---

## 15 min — Meta Instagram (krok za krokom)

### Min 0–2 · Env overlay

```bash
MERGE=1 ./scripts/operator-oauth-env-init.sh
./scripts/operator-meta-oauth-prep.sh
```

Skopíruj **Redirect URI** (presne):

```
https://queenswarm.love/api/auth/callback/oauth
```

### Min 2–8 · Meta Developer Console

1. Otvor https://developers.facebook.com/apps/ → **Create App** → typ **Business**
2. Pridaj produkty:
   - **Instagram Graph API**
   - **Facebook Login for Business** (alebo Facebook Login)
3. **Settings → Basic** → skopíruj **App ID** + **App Secret**
4. **Facebook Login → Settings → Valid OAuth Redirect URIs** → vlož redirect URI vyššie
5. Instagram účet musí byť **Business/Creator** prepojený s **Facebook Page**

### Min 8–10 · Hive env

Do `.env.prod.oauth`:

```bash
OAUTH_META_CLIENT_ID=your_app_id
OAUTH_META_CLIENT_SECRET=your_app_secret
```

```bash
REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh
```

### Min 10–13 · Queenswarm UI

1. **Integrations → Marketplace** → Install **Instagram · Meta Graph**
2. (Voliteľne) Install **Facebook · Meta Graph Pages**
3. **Integrations → Hub** → **Connect** pri Instagram · Meta Graph (hosted OAuth)
4. Over: Execution Studio → **Social publish** → sekcia **Meta accounts** (`ig_user_id`, `page_id`)

### Min 13–15 · Simulate → live

1. Execution Studio → **Publish Queue** → schváľ pack (ak ešte nie je approved)
2. Social publish → **Simulate** na approved pack
3. Live flip (overí simulate + OAuth):

```bash
RUN_SIMULATE=1 CONFIRM_LIVE=1 ./scripts/operator-publish-live-rollout.sh
```

Alebo manuálne:

```bash
CONFIRM_LIVE=1 ./scripts/operator-publish-live-enable.sh
POST_DEPLOY_HEALTH=1 ./scripts/deploy-prod.sh --env-file .env.prod
```

---

## Venice connector (publish onboarding krok)

Voliteľné pre auto `media_url` v publish packoch:

```bash
./scripts/operator-venice-connector-prep.sh
# ak máš kľúč: VENICE_API_KEY=... ./scripts/operator-venice-connector-prep.sh
```

UI: Integrations → Marketplace → **Venice AI · MCP Hub** → Install → Hub → nastav Bearer token → **Test connection**.

Env hook (voliteľné):

```bash
PUBLISH_PACK_VENICE_MEDIA_HOOK_ENABLED=true
```

---

## Overenie

```bash
./scripts/operator-publish-lane-status.sh
./scripts/operator-social-oauth-status.sh
RUN_SIMULATE=1 ./scripts/operator-publish-simulate-gate.sh
```

Očakávané po live flip:

| Metrika | Cieľ |
|---------|------|
| `publish_onboarding_pct` | ≥ 90% |
| `oauth_env_configured` | ≥ 1 |
| `live_publish_enabled` | true |
| `simulate_gate` | pass |

---

## Časté chyby

| Problém | Riešenie |
|---------|----------|
| `oauth_client_not_configured` | Chýba `OAUTH_META_*` → redeploy |
| Prázdne Meta accounts | IG nie je Business alebo chýba Page link |
| Live flip odmietnutý | Najprv `RUN_SIMULATE=1` simulate gate |
| Onboarding 36% | OAuth + Venice + live flip — pozri `./scripts/operator-publish-lane-status.sh` |

---

## Súvisiace

- [`OPERATOR_META_INSTAGRAM_OAUTH.md`](OPERATOR_META_INSTAGRAM_OAUTH.md)
- [`OPERATOR_FIRST_LIVE_POST.md`](OPERATOR_FIRST_LIVE_POST.md)
- [`OPERATOR_SOCIAL_OAUTH_SETUP.md`](OPERATOR_SOCIAL_OAUTH_SETUP.md)
