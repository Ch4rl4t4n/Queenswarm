# Operator vertical packs (Moneta · Marketing · Trading)

Updated: 2026-06-05

Canonical design for **P10 Track N** — low-effort operator packs inspired by Jun 2026 video/X batch. **No parallel apps** — extend Brain Pack, harness profiles, rubrics, goal templates, publish/trading lanes.

**Roadmap:** [`ROADMAP.md`](ROADMAP.md) Track N · **Triage log:** [`ROADMAP_EXCELLENCE_RECOMMENDATIONS.md`](ROADMAP_EXCELLENCE_RECOMMENDATIONS.md)

---

## Operator context

| Vertical | Daily job | Queenswarm lane today | Track N closes |
|----------|-----------|----------------------|----------------|
| **Moneta investments (PO/PM)** | Hypothesis → stakeholder alignment → research brief → delivery tracking | General harness · Research workspace · DA template (planned) | Grill intake · investment brief template · `investments` profile |
| **External marketing** | Brand-consistent creatives · simulate before publish | Publish lane · AOS1 `marketing` · letagentscook | Brand pack · creative rubric · campaign wizard |
| **Trading / betting** | Thesis → probability → risk gate → paper/live | Trading cockpit · AOS1 `trading` · Polymarket evaluators | Thesis brief template · Koah-style kill criteria |

**Security (Moneta):** never paste client PII, account numbers, or unreleased product specs into cloud LLM without approval — use Brain Pack **Instructions** + anonymized briefs only. Prefer **LOC sovereign mode** for sensitive drafts when shipped.

---

## Video & signal triage (Jun 2026 batch)

| Source | Thesis | Verdict | Action |
|--------|--------|---------|--------|
| [Simon — brand context files](https://www.youtube.com/watch?v=yh_fZZVbNwc) | Voice + body-of-work + visual identity as injectable context | 🟡 UX gap | **NP3** Brand Context Pack |
| [Kun Chen — 40 PRs/day](https://www.youtube.com/watch?v=88B6DimMD2g) | Lavish planning · Treehouse parallel agents · No Mistakes review | ✅ ahead / ⛔ clone | **LOOP1** + Queen Maintainer — skip Treehouse |
| [Hermes + Ollama private OS](https://www.youtube.com/watch?v=yaMcm3sQswc) | Local agent + markdown memory | ✅ Track M | **LOC1–4** — do not duplicate |
| [Pi agent / OpenClaw hooks](https://www.youtube.com/watch?v=FJxgz5pN4wU) | Minimal harness · TS hook extensions | ⛔ skip | Document pattern only — harness richer |
| [Jerry Liu — context is moat](https://www.youtube.com/watch?v=PJ-3hXAUotI) | Document/data layer for agents | ✅ ahead | Hive Mind + **DA** — no new stack |
| [Nate — grill-me skill](https://www.youtube.com/watch?v=c0kaKxM2pHg) | Relentless interview → knowledge doc | 🟡 skill exists, no wizard | **NP1** Stakeholder Grill wizard |
| [Nate — Claude Code tier list](https://www.youtube.com/watch?v=vfWTyEreOEc) | Knowledge + automation over novelty | ✅ use today | Skills + Brain Pack — no build |
| [Austin Marchese — build right things](https://www.youtube.com/watch?v=faPA8odcjpY) | Customer/problem validation before build | 🟡 partial | **NP1** + **NP4** — not full Listen Labs |
| [Rasmic — not plan mode](https://www.youtube.com/watch?v=MyRs5hdE7vo) | Closed loops + checkpoints vs wide plan | ✅ Track K | **LOOP1–2** — reference only |
| [Koah — probabilities not guesses](https://www.youtube.com/watch?v=SC4hr_U8298) | Monetize calibrated beliefs · ad/market scoring | 🟡 trading fit | **NP5** thesis brief |
| [Claude lead designer](https://www.youtube.com/watch?v=hKeDfupbA4U) | Iterative design with AI | 🟡 | **NP2** rubric + **TR3** |
| [Pietro — agents killed software](https://www.youtube.com/watch?v=mMuuLocDkog) | Agent surfaces · Magic Path context | ✅ browser module | No new product |
| [Garry Tan — agent workflows](https://www.youtube.com/watch?v=fQmlML9Lay4) | Full-stack agent workflow series | 🟡 | **AL1** timeline — not new harness |
| [Mark Kashef — 6 workflows](https://www.youtube.com/watch?v=g9b9G8dcS8Y) | Dynamic Claude workflows | ✅ skill bundles | Use Mission Kanban + bundles today |
| [Marina Wyss — $300K skills](https://www.youtube.com/watch?v=lxYpYQ-v3is) | Generic AI engineer skill list | ⛔ skip | Factory catalog covers sell side |
| [Karpathy move for Claude Code](https://www.youtube.com/watch?v=4fXYv7MXIpo) | Ecosystem commentary | ⛔ skip | — |
| [Andrew Ng — 30 min app](https://www.youtube.com/watch?v=ff3j4olCUig) | No-code app from prompt | ⛔ skip | Not operator OS scope |
| [David Senra — 400 founders](https://www.youtube.com/watch?v=xXsleu4-kd8) | Founder mode · fewer decisions | 🟡 philosophy | Brain Pack **decisions** note — optional |
| [Listen Labs — Alfred Wahlforss](https://www.youtube.com/watch?v=Rumft-rsEu4) | AI-moderated customer research at scale | ⛔ full platform | **NP1** internal grill only (no 30M panel) |
| [Riverflow 2.5](https://x.com/riverflow_ai) | Brand-tuned image gen · **operator scoring rubric** | 🟡 rubric idea | **NP2** creative rubrics — no Riverflow API required |

---

## Use today vs after ~2026-06-08

| Need | Use today | After Track N |
|------|-----------|---------------|
| Moneta research session | `/tasks` → dispatch · Research workspace · Brain Pack instructions (no bank PII) | **NP4** brief template · **NP7** investments profile |
| Stakeholder / self clarity | Skill `grill-me` in session manually | **NP1** 15-min wizard → brief artifact |
| Marketing post | Publish lane onboarding · AOS1 **marketing** profile · simulate queue | **NP3** brand pack · **NP2** creative rubric · **NP6** campaign wizard |
| Trading idea | AOS1 **trading** · paper cockpit · `polymarket-prediction-evaluator` | **NP5** thesis doc → preflight checklist |
| Batch video intel | Social Intel forager · paste URL in task note | **NP8** URL batch → summary task |
| Sensitive drafts | Cloud LLM + redaction rules in Instructions | **LOC1–4** local sovereign |

---

## Track N specifications

### NP1 — Stakeholder Grill wizard

**Signal:** grill-me (Nate) · Listen Labs (internal slice only)

**What:** Settings or Mission Kanban entry: „Grill my brief“ → 8–12 structured questions (problem, user, success metric, compliance unknowns, kill criteria) → markdown artifact in task workspace → optional dispatch to research session.

**Reuses:** `grill-me.md` · session supervisor · task workspace · critic optional

**Moneta:** Monday standup prep · PRD sanity check before eng sync.

**Est.:** 2–3 d · **Priority:** P1 · **Status:** ✅ shipped (`/tasks` grill wizard + API)

---

### NP2 — Creative rubric presets (Riverflow pattern)

**Signal:** [Riverflow 2.5 scoring rubric](https://x.com/riverflow_ai)

**What:** Add `marketing-creative` + `brand-compliance` templates in `rubric_templates.py`. Publish simulate step shows weighted score (composition, accuracy, CTA clarity, brand voice). LOOP5 preset for bulk copy variants.

**Reuses:** `rubric_templates` API · publish simulate · **LOOP1** closed loop

**Marketing:** Score carousel/copy before queue — no image model integration required initially.

**Est.:** 1–2 d · **Priority:** P1

---

### NP3 — Brand Context Pack

**Signal:** Simon Scrapes brand context files

**What:** Extend Brain Pack curated memory with **Brand** tab: voice bullets, forbidden claims, hex/logo refs (URLs only), example posts, competitor tone notes. Injected in marketing profile sessions only (token cap via **MEM4**).

**Reuses:** `seed-brain-pack` · curated memory API · AOS1 marketing profile

**Est.:** 2 d · **Priority:** P1

---

### NP4 — Investment / product brief goal template

**Signal:** Jerry Liu document layer · Moneta PO workflow

**What:** OW7 goal template `investment-product-brief`: sections Problem · Audience · KPI · Regulatory notes · Open questions · Sources to fetch. One-click dispatch with Research Bee + `grill-me` + Hive Mind recall.

**Reuses:** `swarm-wizard-templates` · OW7 picker · **DA4** wizard pattern (lighter)

**Est.:** 1–2 d · **Priority:** P0 (Moneta daily) · **Status:** ✅ shipped (`investment-product-brief` preset)

---

### NP5 — Trading thesis brief template

**Signal:** Koah — probabilities not guesses

**What:** Goal template `trading-thesis`: market · implied prob · your edge · position size cap · kill criteria · link to paper/live preflight. Session must pass `real-money-risk-gate` before live lane.

**Reuses:** Trading cockpit · AOS1 trading · existing risk validator

**Est.:** 2 d · **Priority:** P1

---

### NP6 — Campaign launch wizard (external projects)

**Signal:** Riverflow one-tool workflow · publish onboarding

**What:** Apps & Tools Marketing: 4-step wizard — pick brand pack → draft copy → rubric score ≥ threshold → simulate publish. Single snapshot API for checklist state.

**Reuses:** **NP2** · **NP3** · `publish_operator_onboarding` · media agency panel patterns

**Est.:** 2–3 d · **Priority:** P1

---

### NP7 — AOS1 `investments` harness profile

**Signal:** Operator vertical switching

**What:** Fifth profile in `harness_project_profiles.py`: skill slugs `grill-me`, `decision-frameworks`, research playbook; CBO lane `research`; default goal hint for anonymized investment product work.

**Reuses:** AOS1 CBO panel · profile switcher (already shipped for 4 profiles)

**Est.:** 1 d · **Priority:** P0 · **Status:** ✅ shipped (5th harness profile)

---

### NP8 — Video URL batch → intel brief

**Signal:** Operator pasting YouTube lists (this conversation)

**What:** Mission Kanban or Foragers: paste 1–20 URLs → Celery fetch title/oEmbed + existing transcript path if available → single markdown digest → wiki capture or triage task. No Ask-YouTube dependency.

**Reuses:** Social intel scrape · **DG6** discovery · SB1 wiki capture

**Est.:** 2–3 d · **Priority:** P2 (nice for your review workflow)

---

## Deduplication map

| Track N | Also satisfies |
|---------|----------------|
| NP1 | MEM2 cited answers (brief cites grill Q&A) |
| NP2 | TR3 · LOOP1 · LOOP5 publish preset |
| NP3 | MEM3 injection strip · marketing profile |
| NP4 | DA4 (lighter) · DG7 dispatch |
| NP5 | Trading Phase I preflight docs |
| NP6 | MK6 marketing proof · publish lane |
| NP7 | AOS1 extension only |
| NP8 | DG1/DG6 partial · SIG operator workflow |

**Do not build:** Listen Labs panel · Riverflow image API · Treehouse multi-agent IDE · Pi/OpenClaw second harness · MemSearch parallel stack.

---

## Recommended build order (Track N)

1. **NP7 + NP4** — Moneta daily (1–2 d total)
2. **NP1** — grill wizard (2–3 d)
3. **NP2 + NP3** — marketing quality (3–4 d)
4. **NP5 + NP6** — trading thesis + campaign wizard (4–5 d)
5. **NP8** — batch video intel (optional)

Run after or parallel to **LOC1–4** if Moneta sensitivity matters; marketing/trading items are cloud-OK with simulate-first.

---

## Operator daily loops (target)

### Moneta PM (15 min morning)

1. Switch harness → **Investments** (**NP7**)
2. New brief from template (**NP4**) or Grill yesterday's idea (**NP1**)
3. Dispatch research session → Kanban tracks lineage
4. Weekly: **DA** workspace for metrics deck (Track L)

### External marketing (campaign)

1. Harness → **Marketing** (AOS1 today)
2. Brand pack loaded (**NP3**)
3. Campaign wizard → rubric pass (**NP6** + **NP2**)
4. Simulate publish → approve live

### Trading / betting

1. Harness → **Trading**
2. Thesis brief (**NP5**) → evaluator session
3. Paper P&L review → live only after risk gate + operator approve

---

## Track O — Learning Loop Studio (CyrilXBT signal)

**Signals:** [Obsidian trading journal thread](https://x.com/cyrilXBT/status/2064928168105136433) · [n8n + Obsidian business brain](https://x.com/cyrilXBT/status/2064883165169140169)

**Verdict:** 🟡 **60% already in harness** (Wiki Layer, Obsidian export/sync, overnight P&L digest, second-brain capture) · 🔴 **missing** = one configurable studio + structured trade loop + mistake recall.

**Product shape:** Small panel in **Apps & Tools → Trading Journal** (not new hive):

```
[ Studio settings ]  fields · cron · Obsidian folder · tags
[ Timeline ]         manual entries + imported paper fills
[ Pattern strip ]    30d / 90d — tags, edge score, repeat mistakes
[ Actions ]          Run review now · Export vault · Open thesis (NP5)
```

**Overnight loop (TJ3):** paper fill / closed position → draft „what worked / mistake“ → operator approve → wiki page + Hive Mind → **TJ5** inject before next trade session.

**⛔ Do not build:** n8n visual editor · separate Obsidian app · autonomous live trade changes.

See [`ROADMAP.md`](ROADMAP.md) Track O (TJ1–TJ7).

---

## Track P — Broker Agent Lane (Ryan Doser / Robinhood MCP)

**Signal:** [YouTube — Robinhood + Claude MCP](https://www.youtube.com/watch?v=w4QrQdulH0g)

**Can we do the same?** **Áno architektonicky** — MCP + session + broker tools. **Nie 1:1 dnes** — nemáme Robinhood preset ani HITL order queue v UI. **Polymarket** už pokrýva prediction markets s lepšími guardrails.

**Minmax panel (target — 1 tab v Trading Cockpit, nie nová app):**

```
Connect → Guardrails → Activity
  MCP status     max order / daily cap    audit + approvals
  OAuth helper   kill switch              last 20 calls
```

**Roadmap:** Track P **RA1–RA5** in [`ROADMAP.md`](ROADMAP.md). Build **RA3→RA5** first (Polymarket), then **RA1→RA2** (Robinhood US).

---

## Track Q — Mission Home & Guided UX (cross-cutting)

**Signal:** [Hermes Agent OS / Mission Control](https://www.youtube.com/watch?v=egeUmkhdcM4)

All vertical packs (N/O/P) and daily operator work **enter through Process Rail** — not parallel side doors.

**Canonical doc:** [`OPERATOR_MISSION_HOME_UX.md`](OPERATOR_MISSION_HOME_UX.md) · **Roadmap:** Track Q **UX0–UX10**

**Build first for clarity:** UX0 → UX1 → UX2 → UX3 → UX6 (before heavy studio builds).
