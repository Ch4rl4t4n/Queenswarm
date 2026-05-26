# X (Twitter) — OAuth 2.0 setup (hosted consent)

Návod pre **queenswarm.love** tweet publish cez X API v2. Secrets len v `.env.prod.oauth`.

**Detail Meta/IG:** [`OPERATOR_META_INSTAGRAM_OAUTH.md`](OPERATOR_META_INSTAGRAM_OAUTH.md)

---

## 0. Rýchly checklist

```bash
./scripts/operator-x-oauth-prep.sh
# vyplň OAUTH_X_* v .env.prod.oauth
REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh
```

UI: Marketplace → **X (Twitter) · API v2** → Hub → **Connect**

---

## 1. X Developer Project

1. https://developer.x.com → **Projects & Apps** → Create Project + App
2. Typ: **Web App** (OAuth 2.0)
3. **User authentication settings** → zapni OAuth 2.0
4. **App permissions:** Read and write
5. **Type of App:** Web App

---

## 2. Redirect URI

```
https://queenswarm.love/api/auth/callback/oauth
```

(Presná hodnota z `./scripts/operator-oauth-env-prep.sh`)

**Callback URL / Redirect URI** v X Developer portal musí sedieť **bajtovo**.

---

## 3. Env na hive

`.env.prod.oauth`:

```bash
OAUTH_X_CLIENT_ID=your_client_id
OAUTH_X_CLIENT_SECRET=your_client_secret
```

```bash
REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh
```

---

## 4. Scopes (automaticky pri Connect)

Queenswarm žiada:

- `tweet.read`
- `tweet.write`
- `users.read`
- `offline.access` (refresh token)

OAuth flow používa **PKCE (S256)** — povinné pre X API v2.

---

## 5. Connect + overenie

1. **Integrations → Marketplace** → Install **X (Twitter) · API v2**
2. **Integrations → Hub** → **Connect** pri X
3. Execution Studio → Social publish → sekcia **X account connected** ukáže `@username`
4. API probe:

```bash
curl -sS -H "Authorization: Bearer $TOKEN" \
  https://queenswarm.love/api/v1/social-publish/x-account | jq .
```

---

## 6. Publish flow

1. Publish pack `"channel": "twitter"` alebo `"x"` — body max 280 znakov (auto-truncate)
2. Publish Queue → Approve
3. Social publish → **Simulate** → **Live** (po `SOCIAL_PUBLISH_LIVE_ENABLED=true`)

---

## Časté chyby

| Problém | Riešenie |
|---------|----------|
| `oauth_client_not_configured` | Chýba `OAUTH_X_*` → redeploy |
| `token_exchange_failed` | Redirect URI mismatch alebo chýba PKCE |
| `403` on `/2/users/me` | App nemá Read and write permissions |
| Live blocked | `SOCIAL_PUBLISH_LIVE_ENABLED=false` — zámerne |

---

Docs: [`OPERATOR_FIRST_LIVE_POST.md`](OPERATOR_FIRST_LIVE_POST.md) · [`OPERATOR_SOCIAL_OAUTH_SETUP.md`](OPERATOR_SOCIAL_OAUTH_SETUP.md)
