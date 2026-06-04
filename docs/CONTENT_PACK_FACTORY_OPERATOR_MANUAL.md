# Content Pack Factory — Operator Manual (English)

Produce, verify, and sell **social content packs** (Instagram, LinkedIn, TikTok, newsletter) via Queenswarm.

**App path:** Apps & Tools → [Content Factory](/apps-tools/content-factory?section=pack-factory#pack-factory) → **Pack factory**  
**Philosophy:** App = production line (simulate-first). Sales = Gumroad or manual upload.

**Related:** `docs/FACTORY_FIRST_REVENUE_OPERATOR_MANUAL.md` (shared scripts + LLM bootstrap)

---

## 0. Pipeline

```
Research (HiveMind heuristics + niche seeds)
    ↓ content_pack_opportunities (ranked)
Build (supervisor — researcher → coder → critic)
    ↓ verified_content_pack_forge
Approve (Agents → Suggestions)
    ↓ tenant_content_packs (Library)
Export (publish_pack.json + PACK.md + LISTING.md)
    ↓ optional Gumroad draft / publish
```

---

## 1. One-time setup

| Step | Where | Hint |
|------|-------|------|
| LLM keys | Settings → AI · LLM keys | **OpenAI gpt-4o-mini** recommended. Factory cannot complete without a working hop. |
| Auto-approve sessions | Agents → Sessions | Enable for solo — avoids `needs_input` stalls. |
| Tavily/Serper (optional) | Settings → API keys | Improves research scores; not required for builds. |
| Gumroad | Integrations → `gumroad_rest` | Or `SKILL_FACTORY_GUMROAD_*` env (shared with Skill Factory). |

**Env:** `CONTENT_PACK_FACTORY_ENABLED=true` (default).

---

## 2. Vertical seeds

Click **Apply vertical starter** in Automation policy — loads 8 Tier-A niches (coaches, B2B SaaS, e-commerce…).

Server (idempotent):

```bash
docker exec queenswarm_prod-backend-1 python scripts/factory_seed_vertical_policies.py
```

Then **Save policy** and **Run research**.

---

## 3. Typical revenue cycle

1. **Run research** — new rows in queue  
2. **Build** on top composite score  
3. Monitor **Agents → Sessions** until complete  
4. **Approve** `verified_content_pack_forge`  
5. **Library → Export** — download bundle  
6. **Gumroad draft** → review → **publish** (if env enabled)

Status:

```bash
docker exec queenswarm_prod-backend-1 python scripts/content_pack_factory_cycle_status.py
```

Full bootstrap:

```bash
./scripts/factory-first-revenue-bootstrap.sh
```

---

## 4. Quality gate

Must pass before forge proposal:

- Critic: `Critic verdict: APPROVE`
- `publish_pack` JSON: `simulate_only=true`, 3+ snippets, CTA, hashtags
- Tag: `content-pack-factory-ready`
- No secret-shaped tokens in body

---

## 5. Operator scripts

| Script | When to use |
|--------|-------------|
| `factory_llm_readiness.py --smoke` | Before first build — must PASS |
| `factory_abort_llm_blocked_builds.py` | Stop doomed builds when LLM down |
| `factory_reset_failed_opportunities.py --apply` | Retry after LLM fix |
| `factory_unblock_builds.py` | Approve `needs_input` + pending forges |
| `content_pack_factory_cycle_status.py` | Queue snapshot + next step |

---

## 6. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `failed` + `missing_publish_pack_json` | Fix LLM keys (OpenAI); rebuild |
| `awaiting_forge` with no forge in Agents | Run cycle status — marks stale rows `failed` |
| Wrong `verified_skill_forge` on pack session | `factory_unblock_builds.py` |
| Build stuck `running` with bad LLM | `factory_abort_llm_blocked_builds.py` |

---

## 7. Research Brief Export (B2B add-on)

Knowledge / Research workspace → **Export B2B pack** — BRIEF.md + EXECUTIVE_SUMMARY + LISTING for consulting deliverables.

---

## 8. Audit

```bash
./scripts/content-pack-factory-audit.sh
```

---

## 9. Tier-A verticals (starters)

- 30-day Instagram calendar for coaches  
- LinkedIn thought-leadership for B2B SaaS  
- TikTok hooks for e-commerce  
- Newsletter launch for indie hackers  
- Black Friday email + social combo  

Full list: `GET /api/v1/content-pack-factory/vertical-seeds`
