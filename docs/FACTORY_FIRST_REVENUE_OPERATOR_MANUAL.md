# Factory First Revenue — Operator Manual (English)

End-to-end bootstrap for **Skill Factory** and **Content Pack Factory** revenue lanes on queenswarm.love.

**App path:** Apps & Tools → Skill Factory / Content Factory → Pack factory  
**Philosophy:** The app is the production line (simulate-first). Sales happen on **Gumroad** or manual upload — not in-app checkout.

---

## 0. Architecture

```
Vertical seeds (Tier-A niches)
    ↓
Research (HiveMind + heuristics)
    ↓ ranked opportunities
Build (supervisor: researcher → coder → critic)
    ↓ verified_*_forge proposal
Operator approve (Agents → Suggestions)
    ↓ tenant library (skills or content packs)
Export bundle + LISTING.md
    ↓ optional Gumroad draft / publish
```

Shared operator scripts live in `backend/scripts/` and are orchestrated by `./scripts/factory-first-revenue-bootstrap.sh`.

---

## 1. Prerequisites (both factories)

| Step | Where | Why |
|------|-------|-----|
| **LLM keys** | Settings → AI · LLM keys | Factory sessions call researcher + coder + critic. **Minimum:** working **OpenAI** (`gpt-4o-mini`) or funded Anthropic. |
| **Auto-approve** | Agents → Sessions | Solo mode — micro-approvals do not stall Celery. |
| **Celery worker** | Deploy / `/health/ready` | Durable factory sessions run on celery-worker. |
| **Gumroad (optional)** | Integrations → `gumroad_rest` or env | Draft/publish from Library. Manual upload works without API. |

### LLM routing (important)

Decomposition chain (default):

1. `xai/grok-3-mini` (primary)
2. `anthropic/claude-haiku-4-5` (fallback)
3. `openai/gpt-4o-mini` (tertiary — **recommended minimum for solo ops**)

**Hint:** Invalid Grok keys in vault or `.env.prod` waste hops before fallback. Run auto-repair (below).

Env flags (Skill + Content Pack Gumroad):

- `SKILL_FACTORY_GUMROAD_LISTING_ENABLED=true`
- `SKILL_FACTORY_GUMROAD_ACCESS_TOKEN=` (or connector vault)
- `SKILL_FACTORY_GUMROAD_PUBLISH_ENABLED=true` (optional — safe default off)

---

## 2. One-command bootstrap

On the production host:

```bash
./scripts/factory-first-revenue-bootstrap.sh
```

This runs (in order):

1. `factory_seed_vertical_policies.py` — idempotent niche seeds
2. `factory_first_revenue_cycle.py` — research + export verify (+ build **only if LLM smoke passes**)
3. `factory_unblock_builds.py` — auto-approve + approve sessions/forges
4. `factory_refresh_skill_exports.py` — disk bundles with LISTING.md hooks from SKILL frontmatter
5. `prepare-gumroad-upload-bundles.sh` — `.tar.gz` per skill on host
6. `factory_llm_auto_repair.py --apply` — remove invalid Grok vault key
7. `factory_llm_readiness.py --smoke` — live LLM ping
8. `factory_abort_llm_blocked_builds.py` — stop building packs when smoke fails
9. Cycle status scripts for both factories

Deploy note: if voice gate blocks deploy after removing Grok, use:

```bash
REQUIRE_VOICE_READY=0 ./scripts/deploy-prod.sh --env-file .env.prod
```

---

## 3. Operator scripts reference

| Script | Purpose |
|--------|---------|
| `factory_llm_readiness.py` | Show effective keys + decomposition chain. `--smoke` = live ping. |
| `factory_llm_auto_repair.py --apply` | Delete invalid Grok from LLM vault when smoke proves bad key. |
| `factory_abort_llm_blocked_builds.py` | Stop `building` content-pack sessions when LLM smoke fails. |
| `factory_reset_failed_opportunities.py --apply` | Move `failed` pack opportunities → `pending` after LLM fix. |
| `factory_refresh_skill_exports.py [out_dir]` | Regenerate skill bundles + LISTING.md (no LLM). |
| `gumroad_listing_snippets.py` | Print copy-paste Gumroad subtitles from export LISTING.md. |
| `skill_factory_export_all_pending.py [--force]` | Stamp `github_exported_at` + write bundles. |
| `content_pack_factory_cycle_status.py` | Queue / library / next-step hint (reconciles stale forges). |
| `skill_factory_cycle_status.py` | Skill library export flags + next step. |

Host export paths:

- Skills: `exports/skill-factory/<slug>/`
- Gumroad archives: `exports/gumroad-upload/<slug>.tar.gz`

---

## 4. Skill Factory — quick revenue (no LLM needed after library fill)

If Library already has verified skills:

1. Refresh exports: `docker exec queenswarm_prod-backend-1 python scripts/factory_refresh_skill_exports.py /tmp/out`
2. Copy to host + pack: `./scripts/prepare-gumroad-upload-bundles.sh`
3. Upload at [gumroad.com/products/new](https://gumroad.com/products/new)
4. Copy text from `LISTING.md` or run `gumroad_listing_snippets.py`

Full guide: `docs/SKILL_FACTORY_OPERATOR_MANUAL.md`

---

## 5. Content Pack Factory — quick cycle

1. **Pack factory → Apply vertical starter** → Save policy
2. **Run research** → ranked queue
3. **Build** top score (≥55% operator script / ≥72% auto-build)
4. After session: **Approve** `verified_content_pack_forge` in Agents
5. **Library → Export** → Gumroad draft (if env) or manual upload

Full guide: `docs/CONTENT_PACK_FACTORY_OPERATOR_MANUAL.md`

### Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Build `failed`, `missing_publish_pack_json` | LLM error instead of pack JSON | Add OpenAI key; run `factory_llm_readiness.py --smoke` |
| `awaiting_forge` stuck | Session ended without valid output | Run `content_pack_factory_cycle_status.py` (auto-marks `failed`) |
| Spurious `verified_skill_forge` on pack session | Legacy mission-prefix bug | `factory_unblock_builds.py` rejects spurious forges |
| Anthropic env set but fails | Zero credits | OpenAI key or top up Anthropic |

---

## 6. Audit

```bash
./scripts/skill-factory-audit.sh
./scripts/content-pack-factory-audit.sh
```

---

## 7. Recommended Tier-A verticals

**Skills:** Cursor agent packs, n8n templates, SEO pipeline, newsletter growth, crypto alerts.  
**Content packs:** 30-day Instagram for coaches, LinkedIn B2B SaaS, TikTok e-commerce hooks, newsletter launch, Black Friday combo.

API: `GET /api/v1/skill-factory/vertical-seeds`, `GET /api/v1/content-pack-factory/vertical-seeds`
