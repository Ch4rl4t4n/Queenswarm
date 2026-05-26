# Production Automation — fázovaný koncept (Instagram & publish lane)

**Status:** Fáza A ✅ · Fáza B ✅ · Fáza C–G ✅ · **Fáza H** ✅ · **First live post** ⏳ (operator)
**Guardrails:** `docs/FEATURE_IMPLEMENTATION_GUARDRAILS.md` — každá ďalšia fáza musí dodržať lazy panel + simulate-first + gate script.

Cieľ: prepojiť **verified výstupy agentov** → **produkčné kanály** (Instagram, newsletter, Notion live, …) bez porušenia **simulate-first**.

---

## Bezpečnostný model (non-negotiable)

```
Agent draft → Simulation / Critic → Operator approve → Publish adapter → Live API
```

- **Nikdy** priamy LLM → Instagram Graph API
- **Vždy** `Execution Studio` approval step pred `live` režimom
- Default connector režim: **`simulate`** (už existuje pre Notion/Gmail)
- Audit log: kto, kedy, čo publikoval

---

## Fáza A — Publish Pack (simulate only) · ~5–7 d

**Status:** ✅ **Shipped** (2026-05-23) — audit: `./scripts/audit-publish-pack-gate.sh`

**Čo:** Agent vyprodukuje **publish pack** — obrázok/copy/hashtags/CTA — uložené do Outputs archive.

| Komponent | Existuje | Doplniť |
|-----------|----------|---------|
| Marketing Ops swarm | ✅ | Instagram pack skill v prompte |
| Execution Studio simulate | ✅ | `publish_pack` artifact type |
| Outputs / Archive UI | ✅ | filter „ready to publish“ |
| Critic verify | ✅ | tag `publish-pack-verified` |

**Výstup pre operátora:** každý deň N balíčkov „pripravených na schválenie“ — **nič live**.

**Gate:** 10+ verified packs bez chyby v simulate.

---

## Fáza B — Approval inbox · ~3–4 d

**Status:** ✅ **Shipped** (2026-05-22) — audit: `./scripts/audit-publish-queue-gate.sh`

**Čo:** jeden UI inbox (Execution Studio **Publish Queue** panel):

- Preview postu (text + media URL)
- Approve / Reject / batch approve
- Edit & re-simulate → link na Outputs regenerate (Phase A)

**API:** `GET /publish-queue` (single snapshot) · `POST /publish-queue/{id}/review` · `POST /publish-queue/bulk-review`

**Reuse:** publish pack tags, Outputs archive, SCV approval UX pattern.

**Flag:** `PUBLISH_QUEUE_ENABLED=true` (default on)

**Gate:** operator schváli 5 postov v simulate bez regresie.

---

## Fáza C — Social publish connectors · ~7–10 d

**Status:** ✅ **Foundation shipped** (2026-05-22) — audit: `./scripts/audit-social-publish-gate.sh`

**Čo:** Phase3 connector templates + unified publish adapter pre:

| Kanál | Connector slug | API |
|-------|----------------|-----|
| Instagram | `instagram_graph` | Meta Graph — media_create → media_publish |
| Facebook | `facebook_graph` | Page feed / photo publish |
| X (Twitter) | `twitter_api_v2` | POST /2/tweets |
| TikTok | `tiktok_content` | Content Posting API — video_publish_init |

**API:** `GET /social-publish` · `POST /social-publish/{id}/simulate` · `POST /social-publish/{id}/publish`

**UI:** Execution Studio → **Social publish** panel (lazy, pod Publish Queue)

**Flags:**
- `SOCIAL_PUBLISH_ENABLED=true` (default on)
- `SOCIAL_PUBLISH_LIVE_ENABLED=false` (default off — simulate until OAuth ready)

**Flow:** Publish Queue approve → Social publish simulate → operator enables live → Live publish

**Env (OAuth — never in repo):** Meta App ID/secret, X client credentials, TikTok client key via Connector Hub.

**Gate:** nainštalovať 4 connectory v Marketplace + simulate 1 post per kanál pred live.

---

## Fáza C (legacy note) — Instagram-only scope

Pôvodný scope len Instagram Graph API — rozšírené na 4 kanály vyššie pri zachovaní simulate-first modelu.

---

## Fáza D — Morning → Publish pipeline · ~4–5 d

**Status:** ✅ **Shipped** (2026-05-22) — audit: `./scripts/audit-morning-publish-pipeline-gate.sh`

**Čo:** napojenie na **My 3 Bees**:

```
08:00  Life OS brief (priorities)
08:15  Content bee draft (Marketing Ops / Content Flywheel)
08:30  Critic verify
09:00  Publish Queue — operator 1-click approve selected
09:05  Live publish (ak Fáza C zapnutá)
```

**API:** `GET /solo-operator/morning-publish-pipeline` (single snapshot) · `POST /solo-operator/morning-publish/run`

**UI:** Settings → AI harness → **Morning → Publish pipeline** (lazy panel pod My 3 Bees)

**Flag:** `MORNING_PUBLISH_PIPELINE_ENABLED=true` (default on)

**Cron:** manuálny trigger cez UI; voliteľný beat backlog (multi-tenant)

---

## Fáza E — Multi-channel · ~ongoing

**Status:** ✅ **Partial shipped** (2026-05-22) — audit: `./scripts/audit-phase-e-publish-gate.sh`

| Kanál | Priorita | Status |
|-------|----------|--------|
| Instagram / Facebook / X / TikTok | P1 | ✅ Fáza C |
| TikTok | P3 | ✅ connector + publish lane |
| Newsletter (Gmail) | P2 | ✅ `gmail_workspace` drafts_send |
| Telegram notify on approve | P2 | ✅ `publish_queue_telegram_notify` |
| Scheduled publish (`scheduled_at`) | P2 | ✅ Celery tick 5 min → simulate |

**Cron:** `hive.morning_publish_pipeline_tick` 08:00 UTC · `hive.scheduled_publish_tick` každých 5 min

**Flags:** `PUBLISH_QUEUE_TELEGRAM_NOTIFY_ENABLED` · `SCHEDULED_PUBLISH_ENABLED`

---

## Fáza F — Publish audit trail · ~2–3 d

**Status:** ✅ **Shipped** (2026-05-22)

**Čo:** história schválení a publikovaní v jednom snapshot-e:

- Publish Queue approve/reject → audit event
- Social publish simulate/live → audit event
- Scheduled publish tick → audit event
- Panel **Publish audit (recent)** v Execution Studio

**API:** súčasť `GET /social-publish` → pole `audit`

**Flag:** `PUBLISH_AUDIT_ENABLED=true` (default on)

**Newsletter:** auto-výber Gmail alebo Resend podľa aktívneho connectora

---

## Fáza G — Trusted auto-publish · ~2–3 d

**Status:** ✅ **Shipped** (2026-05-22) — audit: `./scripts/audit-social-publish-gate.sh`

**Čo:** po N úspešných simulate na kanáli môže operátor prepnúť kanál z **manual** → **auto** a systém publikuje live bez ďalšieho kliknutia (scheduled tick alebo API s `operator_confirmed=false`).

| Vrstva | Správanie |
|--------|-----------|
| Global | `SOCIAL_PUBLISH_TRUSTED_AUTO_ENABLED=false` (default) — musí operátor explicitne zapnúť v prod |
| Tenant | Execution Studio → Social publish → **Enable auto** |
| Kanál | Per-channel Manual / Auto + počítadlo simulates |
| Pack | Musí mať tag `social-publish-simulated` |
| Scheduled | `hive.scheduled_publish_tick` → simulate due packs → optional auto-live |

**API:** `GET /social-publish/trusted-auto` · `PATCH /social-publish/trusted-auto`

**Audit:** `social_live_auto` · `scheduled_live_auto`

**Flags:**
- `SOCIAL_PUBLISH_TRUSTED_AUTO_ENABLED=false` (default off)
- `SOCIAL_PUBLISH_TRUSTED_AUTO_MIN_SIMULATES=5`

**Gate:** 5+ simulate per kanál → enable auto on one channel → scheduled tick auto-live (staging).

---

## Fáza H — Publish lane completion · ~3–4 d

**Status:** ✅ **Shipped** (2026-05-22) — audit: `./scripts/audit-publish-lane-complete-gate.sh`

**Čo:** dokončenie publish lane pre solo operatora bez ďalšieho vývoja pred first live:

| Oblasť | Deliverable |
|--------|-------------|
| Media UX | Embedded preview (Publish Queue + Social publish) |
| Media hooks | Venice image (flag off) · Monid TikTok video (flag off) |
| TikTok | `publish_status_fetch` auto-poll + audit `tiktok_publish_status` |
| Rate limits | Redis snapshot v Social publish paneli |
| Onboarding | 11-krokový checklist + progress bar |
| Admin | Multi-tenant overview v Accounts CMS |
| E2E | `E2E_PUBLISH_LANE=1` Playwright smoke + CI |
| Docs | `OPERATOR_PUBLISH_LANE_MANUAL.md` |

**Master gate:** `./scripts/audit-publish-lane-complete-gate.sh` (pack → queue → social → morning → phase E → hardening)

**Env (všetko default safe — operator zapne až pri setup):**

```bash
PUBLISH_PACK_VENICE_MEDIA_HOOK_ENABLED=false
PUBLISH_PACK_MONID_VIDEO_HOOK_ENABLED=false
TIKTOK_PUBLISH_STATUS_POLL_ENABLED=true
SOCIAL_PUBLISH_TRUSTED_AUTO_ENABLED=false
```

---

## Čo už v kóde máme (netreba stavať od nuly)

- `execution_studio` + `mcp_invoke` simulate/live režimy
- Marketing Ops swarm (`marketing-ops` template)
- `instagram` zmienka v execution context + seed tags
- Researcher → Critic verify lane
- Verified Skill Forge → reusable publish workflow skill
- Solo trio + morning brief orchestrácia

---

## Odporúčané poradie pre teba (solo)

1. ✅ Deploy trio + Brain Pack + **Load starter pack**
2. ✅ **SCV first run** — Execution Studio PR review
3. ✅ **Fáza A–H** — publish lane code-complete (first live = operator only)
4. ⏳ **First live post** — OAuth → Simulate → `SOCIAL_PUBLISH_LIVE_ENABLED=true` → Live
5. ⏳ **Trusted auto** (voliteľné) — po 5+ simulates → `SOCIAL_PUBLISH_TRUSTED_AUTO_ENABLED=true` → kanál Auto

**UI checklist:** Settings → AI harness → **Publish onboarding** (progress %)

**Docs:** `docs/OPERATOR_FIRST_LIVE_POST.md` · `docs/OPERATOR_PUBLISH_LANE_MANUAL.md` · `docs/OPERATOR_SOCIAL_OAUTH_SETUP.md`

**Nespúšťaj live API skôr** — bez Simulate histórie a Publish Queue approve je to risk.

---

## Fáza I — Operator Loop · ~2 d

**Status:** ✅ **Shipped** (2026-05-22) — `./scripts/audit-operator-loop-gate.sh`

**Čo:** jednotné ranné veliteľské centrum — Overnight Dump, Morning Brief, Publish Queue, Trading Cockpit, prioritizované akcie + Telegram digest 07:30 UTC.

---

## Fáza J — Publish Performance Loop · ~1–2 d

**Status:** ✅ **Shipped** (2026-05-22) — `./scripts/audit-publish-performance-gate.sh`

**Čo:** agregácia publish audit trail → simulate success rate, live posts, breakdown po kanáloch, operator insights.

**API:** `GET /publish-performance` · panel v Execution Studio

**Flag:** `PUBLISH_PERFORMANCE_ENABLED=true` (default on)

---

## Fáza K — Trading Phase II (Polymarket only) · ~1 d

**Status:** ✅ **Shipped** (2026-05-22)

**Čo:** Kalshi vyradený z roadmapy — iba **Polymarket** pre real money. Trading Cockpit zobrazuje **Polymarket prep** checklist (Gamma → CLOB → live flag → fund).

**Docs:** `docs/OPERATOR_PREDICTION_MARKETS_SETUP.md` · `docs/OPERATOR_TRADING_COCKPIT_MANUAL.md`

**Operator next:** vault CLOB creds → `PREDICTION_MARKETS_LIVE_TRADING_ENABLED=true` → fund wallet → bot signed orders

---

## Otvorené rozhodnutia (operátor)

- [ ] Osobný vs Business Instagram account?
- [ ] Koľko postov / deň max (rate limit default 10/kanál)?
- [ ] Obrázky: DALL-E / Canva MCP / upload only?
- [ ] Jazyk postov SK / EN / mix?
