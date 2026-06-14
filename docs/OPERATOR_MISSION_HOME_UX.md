# Operator Mission Home & Guided UX

Updated: 2026-06-11

Canonical design for **P10 Track Q** — Hermes-style clarity without losing Queenswarm verify-first depth. **Docs only until operator approves implementation.**

**Status (2026-06-11):** Track Q **UX0–UX10** shipped — Process Rail, Mission Home, memory strip, solo nav, step studios, first-run E2E, session loop chips.

### UX0 sign-off checklist (2026-06-11)

| Check | Status |
|-------|--------|
| 6-step process rail mapped to routes | ✅ |
| Mission Home single snapshot API | ✅ |
| Mobile ≤767 / tablet 768–1023 scoped CSS | ✅ |
| Desktop ≥1024 sidebar+canvas unchanged | ✅ |
| First-run journey E2E (3 viewports) | ✅ `e2e/first-run-journey.spec.ts` |
| 2026 progressive disclosure + 44px touch | ✅ |

**Roadmap:** [`ROADMAP.md`](ROADMAP.md) Track Q · **Signal:** [Claude Agent OS / Hermes Mission Control](https://www.youtube.com/watch?v=egeUmkhdcM4)

---

## Problem statement

Queenswarm is **technically ahead** (swarm, simulate-first, Factory, trading HITL, Hive Mind) but **process + surface area** overwhelm first-time operators. Competing “Agent OS” demos win on:

- One home screen
- Obvious step order
- Memory visible in three files
- Fast “aha” on mobile and desktop

We keep all capabilities — we **re-sequence and re-surface** them.

---

## Deep analysis (Jun 2026)

### Competitive signal (Hermes Agent OS)

| Their strength | Our gap | Keep our moat |
|--------------|---------|---------------|
| Single Mission Control dashboard | No unified home snapshot | Verify + critic + pollen |
| Kanban + agents in one story | Kanban exists but not framed as **the** home | Mission Kanban OW12 ✅ |
| SOUL / MEMORY / USER visible | Brain Pack buried in Settings/Knowledge | Hive Mind + episodic |
| 5-minute first win | LLM + smoke + many entry points | Production security |
| Marketing stack one narrative | Factory / Publish / Lanes parallel | Simulate-first publish |

**Verdict:** Copy **shell + process**, not their stack or hype loops.

### 2026 UI/UX trends (applied to Queenswarm)

Sources: [progressive disclosure & onboarding](https://whatifdesign.co/feeds/blog/saassolar-branding-ui-guidelines) · [dashboard F-pattern & mobile 3–5 cards](https://f1studioz.com/blog/smart-saas-dashboard-design/) · [task-flow before features](https://www.sanjaydey.com/ui-ux-design-trends-2026/)

| Trend | Queenswarm application |
|-------|------------------------|
| **Progressive disclosure** | Home = summary; detail on expand / navigate |
| **Process-first IA** | Global **Process Rail** before feature nav |
| **Time-to-value** | First-run story + sample empty states, not blank canvas |
| **Mobile 3–5 priorities** | Mission Home cards stack; no desktop chrome on mobile |
| **8px grid + 44px touch** | Token audit on mobile/tablet only (`max-lg:`) |
| **Contextual microcopy** | One-line route purpose under every primary heading |
| **Returning vs new user** | Rail shows current step; hide completed setup |

### Responsive rules (non-negotiable)

From [`frontend/lib/breakpoints.ts`](../frontend/lib/breakpoints.ts) + `.cursor/rules/queenswarm-core.mdc`:

| Tier | Width | Mission Home layout |
|------|-------|---------------------|
| **Mobile** | ≤767px | Single column · bottom nav · FAB → New session · **no** duplicate top search bar |
| **Tablet** | 768–1023px | 2-column cards · same mobile chrome (`lg:hidden`) |
| **Desktop** | ≥1024px | **Sidebar + canvas unchanged** · no HiveTopBar · Mission Home in canvas only |

All Track Q CSS scoped to `@media (max-width: 767px)` and `(768px–1023px)` — never alter desktop ≥1024px grid without explicit approval.

---

## Canonical operator process (6 steps)

Every screen maps to **one active step**. User always knows “where am I” and “what’s next”.

```text
① SETUP   → LLM keys · Brain Pack · optional connectors
② PLAN    → Triage · goal template · brief / thesis
③ WORK    → Supervisor session · dispatch · agents run
④ VERIFY  → Critic · simulate · approve / needs_input
⑤ LEARN   → Wiki capture · journal (Track O) · recipes
⑥ DONE    → Deliverable in workspace · Kanban Done · export
```

**Rule:** Primary CTAs on Mission Home follow this order. Advanced modules (Factory, Trading Cockpit, Foragers) open from the **relevant step**, not as parallel daily starts.

---

## Mission Home (target UI)

**URL (solo default):** `/tasks` with **Home** strip above Kanban, or dedicated `/home` alias → same snapshot.

### Desktop canvas (≥1024px)

```text
┌─ Process Rail (6 steps, current highlighted) ─────────────────────────┐
├─ Today brief (3 bullets, verified sources) ───────────────────────────┤
├─ Next 3 actions (operator_next_action) ───────────────────────────────┤
├─ Active sessions (1–3, progress chip → AL1) │ Approvals (5 rows) ────┤
├─ Memory strip (SOUL · MEMORY · USER preview + edit) ──────────────────┤
└─ Kanban board (existing OW12) ────────────────────────────────────────┘
```

### Mobile (≤767px)

- Process Rail → **compact step dots** + current step label
- **Max 5 cards** stacked (brief → actions → approvals → active session → Kanban entry)
- Padding: **16px** horizontal · **12px** card gap · touch targets **≥44px**

### Tablet (768–1023px)

- 2-column: left = brief + actions + memory · right = approvals + sessions
- Kanban horizontal scroll or “Open full board” CTA

### Design quality bar

- **8px spacing grid** (4/8/12/16/24/32)
- Card radius = existing `--qs-radius-lg` · consistent `--qs-border`
- One primary CTA per card (pollen amber) · secondary ghost
- Empty states: illustration + one sentence + single button (never blank)
- Skeleton loaders on every snapshot fetch (existing pattern)

---

## Track Q backlog (implementation when approved)

| ID | Item | Priority | Est. | Reuses |
|----|------|----------|------|--------|
| **UX0** | **UX research lock** — task-flow map · card sort · first-run journey doc · trend checklist sign-off | P0 | 2 d | This doc · OW manual |
| **UX1** | **Process Rail** — 6-step indicator app-wide · current step from tenant state | P0 | 3 d | OW canonical workflow |
| **UX2** | **Mission Home snapshot** — `GET /solo-operator/mission-home` · lazy panel on `/tasks` | P0 | 3–4 d | `operator_next_action` · morning brief · approvals |
| **UX3** | **First-run capability story** — hero “what Queenswarm does” · extend OW5 wizard · sample empty states | P0 | 2–3 d | OW5 · publish onboarding pattern |
| **UX4** | **Progressive solo nav** — 4 primary links · Apps/Agentic OS under **Advanced** | P1 | 2 d | OW4 · OW10 |
| **UX5** | **Memory strip** on Home — SOUL/MEMORY/USER preview · token meter | P1 | 2 d | Brain Pack · **MEM3–MEM4** |
| **UX6** | **Responsive + spacing pass** — mobile/tablet layouts · 8px audit · 44px touch · E2E extend | P0 | 3–4 d | `responsive-shell.spec.ts` · breakpoints.ts |
| **UX7** | **Process-linked studios** — Factory/Trading/Journal entry from rail step only (+ deep links OK) | P1 | 2 d | Apps & Tools modules |
| **UX8** | **Route microcopy** — one-line purpose per primary route (EN operator copy) | P1 | 1–2 d | `section-hints.ts` |
| **UX9** | **E2E first-run journey** — new user → setup → first session → verify (3 viewports) | P1 | 2 d | Playwright · OW19 patterns |
| **UX10** | **Active session cards on Home** — progress + loop chip | P1 | 1–2 d | **AL1** (single build with timeline) |

**Build order:** **UX0 → UX1 → UX2 → UX3 → UX6** (clarity first) → UX4/UX5/UX7/UX8/UX9/UX10.

**⛔ Skip:** Rebuild Hermes OS · second navigation tree on desktop · remove existing modules · auto-hide verify gates.

---

## What stays unchanged (functionality)

- Supervisor sessions · Mission Kanban · Skill Factory · Trading Cockpit · Hive Mind
- Simulate-first · HITL · injection guard · Queen Maintainer
- Tracks N/O/P vertical studios (entry points move, not deleted)
- Desktop shell layout ≥1024px

---

## Success metrics

| Metric | Target |
|--------|--------|
| First-run → first completed session | < 15 min median |
| `% operators using only canonical path week 1` | > 80% |
| Support “where do I start?” | ↓ 50% |
| Mobile Mission Home LCP | < 2.5s cached snapshot |
| `responsive-shell` + first-run E2E | green on CI |

---

## References

- [`OPERATOR_CANONICAL_WORKFLOW.md`](OPERATOR_CANONICAL_WORKFLOW.md)
- [`WHOLE_APP_UI_REORDER.md`](WHOLE_APP_UI_REORDER.md)
- [`FEATURE_IMPLEMENTATION_GUARDRAILS.md`](FEATURE_IMPLEMENTATION_GUARDRAILS.md) — lazy panels · single snapshot API
- [`SOLO_OPERATOR_TRIO_GUIDE.md`](SOLO_OPERATOR_TRIO_GUIDE.md) — Hermes comparison
