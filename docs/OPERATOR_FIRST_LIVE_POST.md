# Operator — First live social post (checklist)

Simulate-first cesta od Brain Pack po prvý **live** post. Pred live vždy dokonči všetky kroky 1–6.

**Kompletný manual:** [`OPERATOR_PUBLISH_LANE_MANUAL.md`](OPERATOR_PUBLISH_LANE_MANUAL.md)

**UI checklist:** Settings → AI harness → **Operator Hub** (next action, OAuth, trusted auto) + **Publish onboarding** (live progress)

Quick status JSON:

```bash
./scripts/operator-publish-lane-status.sh
./scripts/operator-next.sh
```

---

## 1. Brain Pack

**Knowledge → Curated memory** → **Load starter pack** → uprav USER tab → **Save tab**

Alebo jedným príkazom (Brain Pack + demo publish pack + approve):

```bash
./scripts/operator-publish-lane-prep.sh
```

Social OAuth (Meta / X / TikTok) — env stub + vendor guides:

```bash
MERGE=1 ./scripts/operator-oauth-env-init.sh   # ak .env.prod.oauth existuje bez social keys
./scripts/operator-social-oauth-prep-all.sh
REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh
```

Over: Queen bootstrap obsahuje tvoje behavioral instructions.

---

## 2. My 3 Bees

**Settings → AI harness** → skontroluj 3/3 lanes bound → **Run today's cycle**

SCV lane: skontroluj Execution Studio pending proposals (PR-only).

---

## 3. Publish pack (simulate)

Marketing Ops / Content swarm → publish pack s:

```json
{
  "channel": "instagram",
  "body": "…",
  "media_url": "https://…",
  "simulate_only": true
}
```

Tags: `publish-pack-verified`, `simulate-only`

---

## 4. Publish Queue approve

**Execution Studio → Publish Queue** → embedded media preview → **Approve**

Voliteľne: Telegram ping ak máš bota.

---

## 5. OAuth (Connector Hub)

Podľa [`OPERATOR_SOCIAL_OAUTH_SETUP.md`](OPERATOR_SOCIAL_OAUTH_SETUP.md) a kanálových detailov:

| Kanál | Doc | Prep script |
|-------|-----|-------------|
| Instagram / Facebook | [`OPERATOR_META_INSTAGRAM_OAUTH.md`](OPERATOR_META_INSTAGRAM_OAUTH.md) | `./scripts/operator-meta-oauth-prep.sh` |
| X (Twitter) | [`OPERATOR_X_OAUTH_SETUP.md`](OPERATOR_X_OAUTH_SETUP.md) | `./scripts/operator-x-oauth-prep.sh` |
| TikTok | [`OPERATOR_TIKTOK_OAUTH_SETUP.md`](OPERATOR_TIKTOK_OAUTH_SETUP.md) | `./scripts/operator-tiktok-oauth-prep.sh` |

1. Marketplace → nainštaluj kanál (Instagram / X / …)
2. `.env.prod.oauth` → vendor keys → `./scripts/operator-oauth-redeploy.sh`
3. Connector Hub → Connect → Test connection
4. Over v checkliste: **Social OAuth connected** = done

---

## 6. Social Simulate

**Execution Studio → Social publish** → vyber approved pack → **Simulate**

Skontroluj caption, media preview, **Publish audit** záznam.

Opakuj pre každý kanál pred live.

---

## 7. Enable live (host)

Až keď Simulate prešiel pre daný kanál:

```bash
# .env.prod
SOCIAL_PUBLISH_LIVE_ENABLED=true
```

```bash
./scripts/deploy-prod.sh
```

Rate limits (default): 10 / kanál / deň · 30 celkom / deň.

---

## 8. First Live post

1. `./scripts/operator-social-oauth-status.sh` — over social OAuth (nie Gmail)
2. `APPLY=1 ./scripts/operator-live-publish-prep.sh` — zapne live flag + redeploy
3. Social publish → instagram/X pack → **Live** (operator confirm)
4. Over audit: `social_live` + ok
5. Skontroluj kanál natívne (IG app / X timeline)

Voliteľne API smoke: `RUN_LIVE=1 ./scripts/operator-live-publish-gate.sh`

---

## Rollback / stop

```bash
# okamžite vypni live API
SOCIAL_PUBLISH_LIVE_ENABLED=false
./scripts/deploy-prod.sh
```

Schválené packy v queue zostávajú — live sa nespustí.

---

## Súvisiace docs

- [`SOLO_OPERATOR_TRIO_GUIDE.md`](SOLO_OPERATOR_TRIO_GUIDE.md)
- [`PRODUCTION_AUTOMATION_PHASES.md`](PRODUCTION_AUTOMATION_PHASES.md)
- [`OPERATOR_SOCIAL_OAUTH_SETUP.md`](OPERATOR_SOCIAL_OAUTH_SETUP.md)
- [`OPERATOR_META_INSTAGRAM_OAUTH.md`](OPERATOR_META_INSTAGRAM_OAUTH.md)
- [`OPERATOR_X_OAUTH_SETUP.md`](OPERATOR_X_OAUTH_SETUP.md)
- [`OPERATOR_TIKTOK_OAUTH_SETUP.md`](OPERATOR_TIKTOK_OAUTH_SETUP.md)
