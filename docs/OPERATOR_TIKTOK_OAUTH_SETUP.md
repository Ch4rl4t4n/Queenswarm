# TikTok — OAuth setup (Content Posting API)

TikTok vyžaduje **developer app review** pre `video.publish` — OAuth môžeš dokončiť skôr, live publish až po schválení.

---

## 0. Checklist

```bash
./scripts/operator-tiktok-oauth-prep.sh
# OAUTH_TIKTOK_CLIENT_KEY + OAUTH_TIKTOK_CLIENT_SECRET v .env.prod.oauth
REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh
```

Marketplace → **TikTok · Content Posting API** → Hub → **Connect**

---

## 1. TikTok Developer

1. https://developers.tiktok.com → Create app
2. Pridaj **Login Kit** + **Content Posting API**
3. Požiadaj o review pre **Direct Post** / `video.publish`
4. Redirect URI (nižšie) + doména `queenswarm.love`

---

## 2. Redirect URI

```
https://queenswarm.love/api/auth/callback/oauth
```

---

## 3. Env

`.env.prod.oauth`:

```bash
OAUTH_TIKTOK_CLIENT_KEY=
OAUTH_TIKTOK_CLIENT_SECRET=
```

(Pozn.: TikTok používa **client key**, nie client id.)

---

## 4. Scopes (automaticky)

- `user.info.basic`
- `video.publish`

PKCE (S256) — handled server-side.

---

## 5. Publish pack požiadavky

```json
{
  "channel": "tiktok",
  "body": "Caption / popis",
  "media_url": "https://…/video.mp4",
  "simulate_only": true
}
```

**Povinné:** verejne dostupné **video** URL (mp4).

---

## 6. Overenie

```bash
curl -sS -H "Authorization: Bearer $TOKEN" \
  https://queenswarm.love/api/v1/social-publish/tiktok-account | jq .
```

Ak review ešte neprešlo, `creator_info` môže vrátiť 403 — očakávané.

---

Docs: [`OPERATOR_FIRST_LIVE_POST.md`](OPERATOR_FIRST_LIVE_POST.md)
