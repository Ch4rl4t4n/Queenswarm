# Operator — Publish Lane Manual (A → G)

Kompletný postup od agent draftu po **trusted auto-live**. Všetko je **simulate-first** — live až po schválení a OAuth.

**Súvisiace docs:** [`OPERATOR_FIRST_LIVE_POST.md`](OPERATOR_FIRST_LIVE_POST.md) · [`OPERATOR_SOCIAL_OAUTH_SETUP.md`](OPERATOR_SOCIAL_OAUTH_SETUP.md) · [`PRODUCTION_AUTOMATION_PHASES.md`](PRODUCTION_AUTOMATION_PHASES.md)

---

## Architektúra (bezpečnostný model)

```
Marketing Ops swarm
  → Publish Pack Bee (+ Venice image_generate pre media)
  → Critic verify
  → Outputs archive (simulate_only)
  → Publish Queue (operator approve)
  → Social publish (simulate → live)
  → Optional: trusted auto-live (Phase G)
```

**Nikdy:** LLM → priamy live API bez simulate a approve.

---

## 1. Príprava (jednorazovo)

| Krok | Kde | Čo |
|------|-----|-----|
| Brain Pack | Knowledge → Curated memory | Load starter pack → uprav USER → Save |
| My 3 Bees | Settings → AI harness | 3/3 lanes bound |
| Connectors | Integrations → Marketplace | Instagram, X, TikTok, … podľa kanálov |
| OAuth secrets | `.env.prod.oauth` | Vendor keys → `./scripts/operator-oauth-redeploy.sh` |
| Telegram (voliteľné) | Settings → Execution Studio notifications | Bot token + chat ID |

Rýchly bootstrap:

```bash
./scripts/operator-publish-lane-prep.sh
```

---

## 2. Fáza A — Publish Pack (agent)

**Swarm:** Marketing Ops → Publish Pack Bee

Bee musí ukončiť výstup fenced JSON `publish_pack` s `simulate_only: true`.

### Media (obrázok / video)

1. Nainštaluj **Venice MCP** z Marketplace (`venice_mcp`).
2. Bee zavolá `image_generate` (simulate) → verejná HTTPS URL.
3. URL vloží do `media_url` v publish pack JSON.

| Kanál | media_url |
|-------|-----------|
| Instagram / Facebook | `.jpg`, `.png`, `.webp` |
| TikTok | **video** `.mp4` / `.webm` (povinné pred publish) |
| X | voliteľné (text-only OK) |
| Newsletter | voliteľné |

**Validácia:** len `https://`, žiadny localhost, žiadne credentials v URL.

Po critic verify → pack v **Outputs** s tagmi `publish-pack-verified`, `ready_to_publish`.

---

## 3. Fáza B — Publish Queue

**Execution Studio → Publish Queue**

- **Embedded media preview** (thumbnail / video) — nie len link
- Approve / Reject / bulk approve
- Po approve: Telegram ping (ak bot nastavený)

```bash
./scripts/audit-publish-queue-gate.sh
```

---

## 4. Fáza C — Social publish

**Execution Studio → Social publish**

1. Over channel readiness (OAuth, connector active)
2. Vyber approved pack
3. **Simulate** — over caption + media preview + audit záznam
4. Opakuj simulate **5× per kanál** pred trusted auto (Phase G)

### Live (manuálne)

Env:

```bash
SOCIAL_PUBLISH_LIVE_ENABLED=true
```

Potom **Live** s operator confirm.

### Rate limits (panel)

Social publish panel zobrazuje **live quota** (per kanál + global, 24h window). Default: 10/kanál, 30 celkom.

---

## 5. Fáza D — Morning pipeline

**Settings → Morning → Publish pipeline**

Časová os: brief → draft → critic → queue approve → social.

Manuálny trigger cez UI; voliteľný Celery beat.

---

## 6. Fáza E — Scheduled + multi-channel

- `scheduled_at` v publish pack → Celery tick každých 5 min → **simulate**
- TikTok, newsletter (Gmail/Resend), Telegram notify on approve

Env: `SCHEDULED_PUBLISH_ENABLED=true`

---

## 7. Fáza F — Audit trail

Publish audit v Social publish snapshot — queue approve, simulate, live, scheduled.

---

## 8. Fáza G — Trusted auto-live

**Predpoklady:** OAuth + live enabled + 5+ úspešných simulates na kanáli.

Env:

```bash
SOCIAL_PUBLISH_TRUSTED_AUTO_ENABLED=true
SOCIAL_PUBLISH_TRUSTED_AUTO_MIN_SIMULATES=5
```

UI: Social publish → **Enable auto** → kanál **Auto**.

Scheduled tick potom: simulate due pack → ak eligible → **auto-live** + Telegram ping.

Env notify:

```bash
SOCIAL_PUBLISH_TELEGRAM_NOTIFY_ON_AUTO_LIVE=true  # default on
```

---

## TikTok status polling (auto)

Po úspešnom `video_publish_init` (live) backend automaticky volá `publish_status_fetch` až do `PUBLISH_COMPLETE` alebo timeout.

```bash
TIKTOK_PUBLISH_STATUS_POLL_ENABLED=true
TIKTOK_PUBLISH_STATUS_POLL_MAX_ATTEMPTS=6
TIKTOK_PUBLISH_STATUS_POLL_INTERVAL_SEC=2
```

API odpoveď obsahuje `tiktok_status`; UI toast zobrazí stav.

---

## Venice server-side media hook (voliteľné)

Ak publish pack nemá `media_url` (Instagram/FB), server pri archive môže zavolať Venice `image_generate`.

```bash
PUBLISH_PACK_VENICE_MEDIA_HOOK_ENABLED=false  # default off
```

Vyžaduje `venice_mcp` + bearer token v Connector Hub.

---

## Publish onboarding (Settings harness)

11-krokový checklist s progress barom: Brain Pack → Trio → Media → Venice → OAuth → Queue → Simulate → Live → First live → Trusted auto.

API: `GET /solo-operator/publish-onboarding`

**Platform admin:** `GET /admin/publish-lane/onboarding-overview` — progress všetkých tenantov (Accounts CMS).

---

## Monid TikTok video hook (voliteľné)

```bash
PUBLISH_PACK_MONID_VIDEO_HOOK_ENABLED=false
```

Tenant `operator_settings.publish_lane.monid_video`: `provider`, `endpoint`, `input_template`.

Publish pack JSON: `video_url` sa pre TikTok zlúči do `media_url`.

---

## TikTok status audit

Audit kind `tiktok_publish_status` — publish_id, attempts, raw status po live init.

---

## E2E smoke

```bash
E2E_PUBLISH_LANE=1 npm run test:e2e -- e2e/publish-lane.spec.ts
```

---

## Zajtrajší checklist (operator)

- [ ] OAuth keys do `.env.prod.oauth` + redeploy
- [ ] `./scripts/operator-publish-lane-prep.sh`
- [ ] Connector Hub → Connect všetky kanály
- [ ] Marketing Ops run → publish pack s `media_url`
- [ ] Publish Queue → approve (skontroluj **media preview**)
- [ ] Social publish → Simulate (každý kanál)
- [ ] `SOCIAL_PUBLISH_LIVE_ENABLED=true` → 1× manuálny Live
- [ ] (Voliteľné) Trusted auto po 5 simulates

---

## Gate scripty

```bash
./scripts/audit-publish-pack-gate.sh
./scripts/audit-publish-queue-gate.sh
./scripts/audit-social-publish-gate.sh
./scripts/audit-publish-lane-hardening-gate.sh
./scripts/audit-publish-lane-complete-gate.sh
./scripts/operator-release-gate.sh
```

---

## Škálovanie (multi-tenant)

| Vrstva | Izolácia |
|--------|----------|
| Publish packs | `dashboard_user_id` + tenant membership |
| Queue / social | Per-user deliverables |
| Rate limits | Redis keys per `dashboard_user_id` + channel |
| Trusted auto | `tenant.operator_settings.publish_lane.trusted_auto` |
| Telegram | Per-tenant bot + chat v operator_settings |
| Audit | Per-tenant activity log |

Nový tenant: rovnaký flow — OAuth per operator account, policy per tenant, globálne kill switchy v env.

---

## Riešenie problémov

| Symptóm | Riešenie |
|---------|----------|
| TikTok simulate blocked | Pridaj `media_url` s `.mp4` v Outputs |
| Live blocked — rate limit | Počkaj alebo zníž frekvenciu; panel ukáže quota |
| Auto-live nejde | Skontroluj global flag, tenant Enable auto, channel Auto, simulate tag |
| Media preview neukáže | URL musí byť verejné HTTPS; inak fallback link |
| Venice bez URL | Nainštaluj connector + bearer token v Hub |
