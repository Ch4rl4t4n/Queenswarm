# Meta Developer — Instagram + Facebook OAuth (hosted consent)

Krok-za-krokom pre **queenswarm.love** social publish. Secrets len v `.env.prod.oauth` — nikdy do git.

**Pred live:** Publish Queue approve → Social **Simulate** → `SOCIAL_PUBLISH_LIVE_ENABLED=true` → redeploy.

---

## 0. Rýchly checklist

```bash
./scripts/operator-meta-oauth-prep.sh
./scripts/operator-oauth-env-init.sh          # ak ešte nemáš overlay
# vyplň OAUTH_META_* v .env.prod.oauth
REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh
```

UI: **Integrations → Marketplace** → nainštaluj Instagram + Facebook → **Integrations → Hub** → **Connect** (Instagram · Meta Graph).

---

## 1. Meta Developer App

1. https://developers.facebook.com → **Create App** → typ **Business**
2. Pridaj produkty:
   - **Facebook Login for Business** (alebo Facebook Login)
   - **Instagram Graph API**
3. **Settings → Basic** → skopíruj **App ID** a **App Secret**

---

## 2. Redirect URI (povinné)

Zaregistruj **presne** túto URI (získaš aj z `./scripts/operator-oauth-env-prep.sh`):

```
https://queenswarm.love/api/auth/callback/oauth
```

**Facebook Login → Settings → Valid OAuth Redirect URIs** → vlož URI, Enter (musí sa objaviť **šedý tag/chip**), potom **Save changes**.

Queenswarm posiela OAuth s Meta parametrom `IG_API_ONBOARDING` (Instagram use-case apps) — redirect URI musí sedieť **presne** (bez `/v1/`, bez koncového `/`).

Overenie v Meta konzole: **Facebook Login for Business → Settings → Redirect URI Validator** — vlož rovnakú URI, klikni **Check URI**.

---

## 2b. Facebook Login for Business — config_id (Instagram use-case apps)

Ak po Connect vidíš Facebook chybu *„This content isn't available right now“*, app typu **Instagram / Business** potrebuje **Login Configuration**:

1. Meta console → tvoja app **Queenswarm** → vľavo **Facebook Login for Business** → **Configurations**
2. **Create configuration** (názov napr. `Queenswarm IG Publish`)
3. Pridaj permissions:
   - `pages_show_list`
   - `pages_read_engagement`
   - `instagram_basic`
   - `instagram_content_publish`
4. **Save** → skopíruj **Configuration ID** (číslo)
5. Do `.env.prod.oauth`:

```bash
OAUTH_META_CONFIG_ID=1234567890123456
```

6. `REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh`

---

## 3. App settings → Basic (povinné)

| Pole | Hodnota |
|------|---------|
| App domains | `queenswarm.love` |
| Privacy Policy URL | `https://queenswarm.love/privacy` |
| Website | `https://queenswarm.love` |

**App roles:** tvoj FB účet musí byť **Administrator** alebo **Developer** (Development mode).

---

## 4. Env na hive hoste

Do `.env.prod.oauth` (overlay, nie commit):

```bash
OAUTH_META_CLIENT_ID=your_app_id
OAUTH_META_CLIENT_SECRET=your_app_secret
OAUTH_META_CONFIG_ID=your_login_configuration_id
```

Potom:

```bash
REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh
```

---

## 5. Instagram Business účet

- Instagram musí byť **Business** alebo **Creator**
- Prepojený s **Facebook Page** (Meta Business Suite)
- V app **Roles** pridaj seba ako Admin/Developer

Bez prepojenia Page → IG neuvidíš `instagram_business_account` v `/me/accounts`.

---

## 6. Connect v Queenswarm

1. **Marketplace** → **Instagram · Meta Graph** → Install
2. **Marketplace** → **Facebook · Meta Graph Pages** → Install (voliteľne pre FB feed)
3. **Connector Hub** → hosted OAuth rail → **Connect** pri Instagram · Meta Graph
4. Po úspechu: Execution Studio → **Social publish** → sekcia **Meta accounts** ukáže `ig_user_id` a `page_id`

Scopes (automaticky pri Connect):

| Kanál | Scopes |
|-------|--------|
| Instagram | `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement` |
| Facebook Page | `pages_show_list`, `pages_read_engagement`, `pages_manage_posts` |

Token sa vymení na **long-lived** (~60 dní) server-side.

---

## 7. Overenie

```bash
# JWT + API (na hive)
curl -sS -H "Authorization: Bearer $TOKEN" \
  https://queenswarm.love/api/v1/social-publish/meta-accounts | jq .
```

Očakávané: `pages[]` s `ig_user_id` pre IG Business účet.

**Simulate:** Execution Studio → Social publish → approved pack → **Simulate** (ig_user_id sa doplní automaticky ak chýba).

---

## 8. Časté chyby

| Problém | Riešenie |
|---------|----------|
| Facebook *„This content isn't available“* | Chýba redirect URI chip + Save, alebo chýba `OAUTH_META_CONFIG_ID` (krok 2b) |
| `oauth_client_not_configured` | Chýba `OAUTH_META_*` v `.env.prod.oauth` → redeploy |
| Prázne `pages[]` | IG nie je Business/Creator alebo nie je prepojený s Page |
| `meta_accounts_http_403` | Chýbajúce scopes alebo app v Development mode — pridaj test usera |
| Simulate OK, Live blocked | `SOCIAL_PUBLISH_LIVE_ENABLED=false` — zámerne, zapni až po Simulate |

---

## Súvisiace

- [`OPERATOR_SOCIAL_OAUTH_SETUP.md`](OPERATOR_SOCIAL_OAUTH_SETUP.md) — všetky kanály
- [`OPERATOR_FIRST_LIVE_POST.md`](OPERATOR_FIRST_LIVE_POST.md) — end-to-end checklist
