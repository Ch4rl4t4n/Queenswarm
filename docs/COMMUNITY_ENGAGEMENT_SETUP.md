# Community Engagement (POS-CE) — setup guide

**Collect → compose → commit (HITL).** Agents find threads and draft replies; you approve before anything goes live.

Pattern source: Rahul Reddit engagement agent — adapted for Queenswarm verify-first stack (not full autopilot spam).

**Roadmap:** POS-CE in [`ROADMAP.md`](ROADMAP.md) · admission gate POS-ARCH

---

## Architecture (whole-app)

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│  COLLECT    │ ──► │   COMPOSE    │ ──► │    VERIFY       │ ──► │   COMMIT     │
│  Foragers   │     │ Marketing    │     │ closed-review   │     │ Publish queue│
│  RSS/Reddit │     │ digest/skill │     │ community-auth  │     │ YOU approve  │
└─────────────┘     └──────────────┘     └─────────────────┘     └──────────────┘
     /foragers           /agents              harness LOOP2            /tasks
```

| Surface | Your job |
|---------|----------|
| [`/foragers`](https://queenswarm.love/foragers) | Add subreddit RSS / Data Monitor intent |
| [`/knowledge#hivemind`](https://queenswarm.love/knowledge) | Scan `engagement-candidate` rows |
| [`/agentic-os#lanes`](https://queenswarm.love/agentic-os) | Marketing lane digest Mon/Wed/Fri |
| [`/agents#sessions`](https://queenswarm.love/agents) | AFK digest + critic APPROVE |
| Digest Inbox → Tasks | Promote digest → review draft replies |
| Publish queue (simulate) | Approve copy-paste or future connector |

---

## What ships in code

| Asset | Purpose |
|-------|---------|
| Skill `community-engagement-playbook` | Draft workflow + guardrails |
| Rubric `community-authenticity` | Anti-spam / helpfulness gate |
| `community_engagement_policy.py` | Caps, Reddit RSS helper, harness block |
| Data Monitor niche **community** | One-line intent → RSS forager |
| Marketing lane | Skill + context caps on routine |
| `seed_community_engagement.py` | Idempotent forager + harness |

**Not included (by design):** Reddit live auto-post connector · unlimited autopilot · repo MEMORY.md

---

## Quick start (5 commands)

```bash
# 1. Verify assets
chmod +x scripts/audit-community-engagement-gate.sh scripts/operator-community-engagement-provision.sh
./scripts/audit-community-engagement-gate.sh

# 2. Provision forager + harness (+ first RSS scrape)
./scripts/operator-community-engagement-provision.sh

# 3. Refresh four-lane marketing skills/context
./scripts/operator-four-lane-provision.sh

# 4. Operator verify
./scripts/operator-solo-readiness-audit.sh

# 5. Hard refresh browser → open /foragers + /agentic-os#lanes
```

---

## Step-by-step operator setup

### 1. Curated memory (brand voice)

**Settings → AI · harness** or **Knowledge → Curated memory**

Add to **BRAND** or **INSTRUCTIONS**:

```markdown
### Community tone (POS-CE)
- Help first, product mention max once and only when thread asks for recommendations
- CZ/SK tone for Najman threads; English for r/LocalLLaMA etc.
- Forbidden: urgency, fake personal stories, link dumps, "DM me for discount"
```

Combine with existing **Najman Marketing Colony** block — do not duplicate firm rules.

### 2. Community forager (collect)

**Automatic (recommended):**

```bash
SCRAPE=1 ./scripts/operator-community-engagement-provision.sh
```

Creates **Community Engagement Intel** with starter feeds:

- `r/Beekeeping` · `r/slovakia` · `r/LocalLLaMA`

**Manual — Data Monitor wizard** (`/foragers#data-monitor-wizard`):

```
Monitor r/Beekeeping and https://www.reddit.com/r/vcelarstvo/ for honey questions — engagement candidates only
```

Reddit URLs auto-convert to `.rss` feeds.

**Manual — add feeds in UI:**

```
https://www.reddit.com/r/YOUR_SUB/.rss
```

### 3. Marketing lane (compose)

**Agentic OS → Lanes → Bootstrap four lanes** (if not done).

Lane **Najman Marketing** now includes:

- Skills: `marketing-campaign-playbook` + `community-engagement-playbook`
- Context caps: max **3** draft replies/digest · **0** live posts/day (simulate)
- Goal step **3b**: drafts from `engagement-candidate` tags

Schedule: Mon/Wed/Fri 09:00 UTC.

### 4. Loop guardrails (verify)

**Settings → harness → Loop guardrails (LOOP2)**

| Setting | Recommended |
|---------|-------------|
| max_turns | 5 |
| min_score | 0.8 (4/5) |
| cost_cap_usd | your session budget |

Closed review uses rubric **`community-authenticity`** for reply drafts.

### 5. Daily operator loop (5 min)

1. **Foragers** — overnight RSS ingest OK?
2. **Knowledge** — filter tag `engagement-candidate`
3. **Agents → Sessions** — marketing digest completed?
4. **Digest Inbox** (`/agentic-os#lanes`) — promote to Task
5. **Tasks** — review YAML draft replies; approve simulate publish or copy-paste manually

---

## Combine with (recommended stacks)

| Goal | Stack |
|------|-------|
| **Najman CZ marketing** | Community forager + marketing lane + Brand studio rubric |
| **Competitor context** | `competitor-scrape-analyze` + Vcelarstvi Competitor Intel forager |
| **Inbound tech intel only** | Social Intel (YouTube/X) + `social-intel-evaluator` — **not** for outbound |
| **High-signal triage** | Goldmine alerts → Kanban dispatch with skill bundle |
| **Research depth** | Research Bee batch URLs before drafting reply |
| **Quality loop** | POS-LOOP LN1 same-failure-twice + LN2 anti-cheat (when shipped) |
| **Memory compound** | MM8 distill only after APPROVE digest |

### Avoid combining (clutter / risk)

| Don't | Why |
|-------|-----|
| Social intel evaluator on outbound drafts | Wrong skill — inbound scoring only |
| Live X publish + Reddit drafts same session | Mixed channels confuse critic |
| Auto-approve on critic fail | OP1 blocker — false green |
| Multiple community foragers same subreddit | Duplicate alerts — merge feeds |

---

## Procedure reference (HN3 future)

| Procedure | Maps to |
|-----------|---------|
| `/community-engage` | Manual durable session + playbook |
| `/triage-digest` | Digest inbox promote |
| `/memory-review` | Trim INSTRUCTIONS after campaigns |

Until HN1 registry ships: launch **Agents → New session** with goal referencing `community-engagement-playbook`.

---

## Stop rules (mandatory)

| Rule | Default | Where |
|------|---------|-------|
| max_draft_replies_per_digest | 3 | marketing lane `context_payload.community_engagement` |
| max_live_posts_per_day | 0 | same (simulate until you raise) |
| LOOP2 max_turns | 5 | Settings harness |
| same-failure-twice | escalate | POS-LOOP LN1 (planned) |
| operator-approval-gate | live publish | `operator-approval-gate` skill |

To allow live posts later: raise `max_live_posts_per_day` in routine context **only after** Reddit/X connector + OAuth — not before.

---

## Verification checklist

- [ ] `./scripts/audit-community-engagement-gate.sh` → PASS
- [ ] Forager **Community Engagement Intel** active in `/foragers`
- [ ] Knowledge rows with tags `engagement-candidate`, `forager:rss`
- [ ] Curated INSTRUCTIONS contains `## Community Engagement (POS-CE)`
- [ ] Marketing lane skills include `community-engagement-playbook`
- [ ] Digest produces ≤3 reply drafts with `simulate_only: true`
- [ ] No live post without your explicit approve

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Empty Reddit RSS | Reddit may rate-limit; retry scrape; check feed URL ends with `/.rss` |
| No engagement drafts in digest | No recent `engagement-candidate` rows — run forager scrape |
| Critic always fail | Check BRAND voice block; lower min_score temporarily; read rubric feedback |
| Digest auto-approved on LLM error | OP1 — stop session, fix before scaling community lane |
| Too many alerts | Reduce feeds; merge into one forager; use Goldmine dispatch sparingly |

---

## Related docs

- [`SOCIAL_INTEL_SWARM_SETUP.md`](SOCIAL_INTEL_SWARM_SETUP.md) — inbound YouTube/X (combine for intel, not outbound)
- [`SOLO_OPERATOR_FOUR_LANE.md`](SOLO_OPERATOR_FOUR_LANE.md) — marketing lane rhythm
- [`OPERATOR_CANONICAL_WORKFLOW.md`](OPERATOR_CANONICAL_WORKFLOW.md) — Agents primary path
- [`ROADMAP_PERSONAL_OS_FOCUSED.md`](ROADMAP_PERSONAL_OS_FOCUSED.md) — POS-CE backlog

---

## Roadmap — POS-CE

| ID | Item | Status |
|----|------|--------|
| CE1 | Skill + rubric + policy module | ✅ |
| CE2 | Data Monitor community niche | ✅ |
| CE3 | Seed + provision + audit scripts | ✅ |
| CE4 | Marketing lane integration | ✅ |
| CE5 | Procedure `/community-engage` in HN1 registry | ⏳ |
| CE6 | Reddit live connector + daily cap enforcement | ⏳ P2 |
| CE7 | BA4 inbox strip for pending reply drafts | ⏳ P2 |
| CE8 | Verified Recipe Library entry after first approve loop | ⏳ P2 |
