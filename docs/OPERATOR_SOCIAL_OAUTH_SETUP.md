# Operator — Social OAuth setup (Instagram · Facebook · X · TikTok)

Návod pre **Connector Hub** + **Tools Marketplace**. Secrets len cez env / OAuth — nikdy do repa.

**Pred live publish:** Publish Queue approve → Social **Simulate** → potom `SOCIAL_PUBLISH_LIVE_ENABLED=true` v `.env.prod` → redeploy.

---

## 1. Meta — Instagram + Facebook

### Požiadavky
- Meta Developer účet: https://developers.facebook.com
- **Business** alebo **Creator** Instagram účet prepojený s Facebook Page
- App typ: Business

### Kroky
1. **Tools Marketplace** → nainštaluj **Instagram · Meta Graph** a **Facebook · Meta Graph Pages**
2. **`.env.prod.oauth`:** `OAUTH_META_CLIENT_ID` + `OAUTH_META_CLIENT_SECRET` → `./scripts/operator-oauth-redeploy.sh`
3. **Connector Hub** → **Connect** (hosted OAuth) — nie manuálny vault token
4. Over **Meta accounts** v Execution Studio → Social publish (auto `ig_user_id`)
5. Test connection → **Simulate** publish

**Detailný návod:** [`OPERATOR_META_INSTAGRAM_OAUTH.md`](OPERATOR_META_INSTAGRAM_OAUTH.md) · `./scripts/operator-meta-oauth-prep.sh`

### OAuth redirect URI
```
https://queenswarm.love/api/auth/callback/oauth
```
(Zobrazí aj `./scripts/operator-oauth-env-prep.sh`)

### Scopes (automaticky pri Connect)
   - `instagram_basic`, `instagram_content_publish`
   - `pages_manage_posts`, `pages_read_engagement`
5. **Connector Hub** → Connect → dokonči OAuth
6. Test connection → **Simulate** publish v Execution Studio

### Pri publish packu / API
- Instagram: `ig_user_id` sa **auto-doplní** z Meta OAuth (alebo manuálne v simulate body)
- Facebook Page: nastav `page_id`

---

## 2. X (Twitter)

### Požiadavky
- Developer portal: https://developer.x.com
- App s **OAuth 2.0 user context** (read + write)

### Kroky
1. Marketplace → **X (Twitter) · API v2**
2. **`.env.prod.oauth`:** `OAUTH_X_CLIENT_ID` + `OAUTH_X_CLIENT_SECRET` → redeploy
3. X Developer → OAuth 2.0 Web App · **Read and write** · Callback URL nižšie
4. **Connector Hub** → **Connect** (PKCE automaticky)
5. Over `@username` v Social publish paneli

**Detail:** [`OPERATOR_X_OAUTH_SETUP.md`](OPERATOR_X_OAUTH_SETUP.md) · `./scripts/operator-x-oauth-prep.sh`

### Callback URL
```
https://queenswarm.love/api/auth/callback/oauth
```

---

## 3. TikTok

### Požiadavky
- TikTok for Developers: https://developers.tiktok.com
- Content Posting API approval (môže trvať review)

### Kroky
1. Marketplace → **TikTok · Content Posting API**
2. **`.env.prod.oauth`:** `OAUTH_TIKTOK_CLIENT_KEY` + `OAUTH_TIKTOK_CLIENT_SECRET` → redeploy
3. TikTok Developer → Login Kit + Content Posting API → **app review** pre `video.publish`
4. **Connector Hub** → **Connect** (PKCE)
5. Publish pack **musí obsahovať video** v `media_url` (mp4 URL verejne dostupné)
6. Simulate → potom Live (až po review)

**Detail:** [`OPERATOR_TIKTOK_OAUTH_SETUP.md`](OPERATOR_TIKTOK_OAUTH_SETUP.md) · `./scripts/operator-tiktok-oauth-prep.sh`

---

## 4. Newsletter — Gmail alebo Resend

| Provider | Marketplace template | OAuth / key |
|----------|---------------------|-------------|
| Gmail | Gmail · Google Workspace | Google OAuth |
| Resend | Resend · Transactional Email | Bearer API key |

Systém **automaticky vyberie** prvý aktívny connector (Gmail pred Resend).

Publish pack: `"channel": "newsletter"` + subject v `title`, body v `body`.

---

## 6. Zapnutie live publish

```bash
# .env.prod — až po úspešnom Simulate pre každý kanál
SOCIAL_PUBLISH_LIVE_ENABLED=true
```

```bash
./scripts/deploy-prod.sh
```

Rate limits (default): **10 live / kanál / deň**, **30 celkom / deň**.

---

## 7. End-to-end checklist

1. Marketing Ops swarm → publish pack (`simulate_only: true`)
2. **Publish Queue** → Approve
3. Telegram ping (ak bot nastavený) → link na Social publish
4. **Social publish** → Simulate
5. OAuth OK → Live (operator confirmed)
6. **Publish audit** sekcia — over záznam

Docs: `docs/SOLO_OPERATOR_TRIO_GUIDE.md` · `docs/PRODUCTION_AUTOMATION_PHASES.md`
