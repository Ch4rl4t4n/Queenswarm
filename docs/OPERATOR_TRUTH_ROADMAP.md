# Operator Truth Roadmap — Personal OS execution (canonical)

> **Updated:** 2026-06-05  
> **Status:** Single source of truth for **what to run daily** vs **what to build next**.  
> Historical waves (POS-H…POS-O) live in [`ROADMAP.md`](ROADMAP.md) — reference only.

**North star:** Otvoríš `/tasks` → 3 Jarvis kroky → schváliš 1 verified AFK výstup → večer `/ballroom` Dump & Sleep — **bez false APPROVE**.

---

## Four layers (never confuse again)

| Layer | Meaning | Gate |
|-------|---------|------|
| **L1 Platform** | Shipped code you can touch today | Feature audits ✅ |
| **L2 Discipline** | AFK tells the truth (no false pass) | `audit-personal-os-discipline-gate.sh` |
| **L3 Adoption** | Config + procedures + daily habit | Operator ops + HN/CE/JAR |
| **L4 Optional** | Voice, Reddit live, Slack | Only after L2 green |

**Rule:** L1 at 100 % + L2 red = **partial**, not production-trust. Readiness audits enforce this.

---

## Daily stack (use today — L1)

| Step | Route | Module |
|------|-------|--------|
| Morning triage | `/tasks` | Jarvis strip · Kanban |
| Delegate work | `/agents` | Sessions · four-lane digests |
| Intel | `/foragers` · `/knowledge` | Social Intel · CE forager · Brain Pack |
| Lanes | `/agentic-os#lanes` | Digest inbox → promote |
| Approvals | Approval Inbox · publish queue | J3 email · compound drafts |
| Evening | `/ballroom` | Dump & Sleep |
| Weekly | Knowledge → evolution | J1 compound · I3 reflection |

Setup guides: [`JARVIS_PERSONAL_ADVISOR_SETUP.md`](JARVIS_PERSONAL_ADVISOR_SETUP.md) · [`COMMUNITY_ENGAGEMENT_SETUP.md`](COMMUNITY_ENGAGEMENT_SETUP.md)

---

## Sprint packages (merged overlaps — one sprint = one package)

### ST1 — Discipline foundation ✅ P0 (blocks trust)

**Merges:** OP1 · MM8 · LN1

| ID | Deliverable | Audit |
|----|-------------|-------|
| ST1.1 | No auto-approve when critic/LLM fails; real stop + Celery revoke | `pytest tests/test_supervisor_session_control_unit.py` + discipline gate |
| ST1.2 | Distill to INSTRUCTIONS only after APPROVE / digest promote | `pytest tests/test_session_learnings*` |
| ST1.3 | Same-failure-twice → halt loop + needs_input | `pytest tests/test_loop_guardrails*` |

**Exit:** `./scripts/audit-personal-os-discipline-gate.sh` → **PASS** (2026-06-05)  
**Freeze lifted for ST2+** — still no new Mission Home strips until ST2–ST3 green.

---

### ST2 — AFK routing cleanup ✅ P0

**Merges:** OP2 · OP3 · LN2

**Exit:** `./scripts/audit-personal-os-st2-gate.sh` → **PASS**

---

### ST3 — Proof sprint ⏳ P0

**Merges:** OP4

**Exit:** `./scripts/operator-tech-scv-proof.sh` · `./scripts/audit-jarvis-intelligence-gate.sh`

---

### ST4 — Config adoption ⏳ P1 (operator)

**Merges:** CE ops · JAR ops · JA2 · OP5/OP6

**Exit:** `./scripts/operator-community-engagement-provision.sh` · curated MISSION filled

---

### ST5 — Procedures package ✅ P1

**Merges:** HN1 · HN2 · HN3 · MM7 · CE5 · JA3 · JA4

**Procedure map** (`procedures/` registry):

| Slash | File | Purpose |
|-------|------|---------|
| `/advisor` | `procedures/advisor.md` | Jarvis 3-step loop · personal-advisor-playbook |
| `/advisor-eval` | `procedures/advisor-eval.md` | H6 scorecard checklist |
| `/community-engage` | `procedures/community-engage.md` | CE playbook · marketing lane drafts |
| `/memory-review` | `procedures/memory-review.md` | Curated INSTRUCTIONS editor |
| `/triage-digest` | `procedures/triage-digest.md` | Four-lane digest inbox → promote |
| `/coach-compound` | `procedures/coach-compound.md` | Weekly eval + compound ritual (ST7) |

**Exit:** `./scripts/audit-personal-os-procedures-gate.sh` → **PASS**

---

### ST6 — UX cohesion ✅ P2

**Merges:** HN4+JA6 · LN3+LN5 · CE7+CE8

Mission Home `strategic_today_strip` + `afk_running_strip` (backend API).

---

### ST7 — Metrics & memory polish ✅ P2

**Merges:** HN5 · JA5 · MM9 · MM10

`personal_os_eval_metrics_service` · `procedures/coach-compound.md`

---

### ST8 — Optional ⏸ P3

CE6 Reddit live · JA7 voice · OP7 Slack · OP8 GitHub · OP9 automation · HN6 learn-from-source · Track M local LLM

**Rule:** Each requires ST1–ST3 green + explicit operator approval.

---

## Anti-drift rules (future features)

| ID | Rule |
|----|------|
| AR1 | **Readiness 100 %** requires L2 discipline gate PASS (not env-only) |
| AR2 | **Max 1 new operator entry per sprint** (procedure OR strip, not both) |
| AR3 | **Mission Home strip budget:** new strip → demote one to Advanced accordion |
| AR4 | **Adoption wave** (new POS-* letter) forbidden until ST1 PASS |
| AR5 | **POS-ARCH AG1–AG5** mandatory — compose, don't fork |
| AR6 | **Verify ritual:** `./scripts/operator-personal-os-truth-gate.sh` weekly |

---

## Audit matrix (tiered)

| Tier | Script | When | Blocks |
|------|--------|------|--------|
| **Core discipline** | `audit-personal-os-discipline-gate.sh` | Every deploy · ST1 | False APPROVE |
| **Operator truth** | `audit-personal-os-truth-gate.sh` | Weekly | L2+L3 status |
| **Platform** | `operator-solo-readiness-audit.sh` | Daily | Caps 100% if discipline fail |
| **Weekly full** | `operator-personal-os-verify.sh` | Weekly | Core vs adoption tiers |
| **Feature** | `audit-*-gate.sh` per module | After module change | Regression |

**Core verify gates (must pass for „functional“):**

- `audit-personal-os-gate.sh`
- `audit-personal-os-discipline-gate.sh`
- `audit-autopilot-gate.sh`
- `audit-jarvis-intelligence-gate.sh`
- `audit-community-engagement-gate.sh`

**Adoption gates (warn if fail, don't block deploy after ST1):** remaining `audit-personal-os-*-adoption-gate.sh` list in verify script.

---

## Mapping old IDs → sprint packages

| Old | Sprint |
|-----|--------|
| OP1, MM8, LN1 | ST1 |
| OP2, OP3, LN2 | ST2 |
| OP4 | ST3 |
| CE ops, JAR ops, JA2, OP5/6 | ST4 |
| HN1–3, MM7, CE5, JA3–4 | ST5 |
| HN4, JA6, LN3–5, CE7–8 | ST6 |
| HN5, JA5, MM9–10 | ST7 |
| CE6, JA7, OP7–9, HN6 | ST8 |

---

## Execution order (final)

1. **ST1** → 2. **ST2** → 3. **ST3** → 4. **ST4** → 5. **ST5** → 6. **ST6** → 7. **ST7** → 8. **ST8**

After **ST3**: entire L1 platform is **trustworthy + proven**. ST4–ST7 = comfort & speed, not survival.

---

## Related

- [`ROADMAP_PERSONAL_OS_FOCUSED.md`](ROADMAP_PERSONAL_OS_FOCUSED.md) — short mirror
- [`ROADMAP.md`](ROADMAP.md) — full backlog + POS-* tracks
- [`PERSONAL_OS_MAINTENANCE.md`](PERSONAL_OS_MAINTENANCE.md) — audit cadence
