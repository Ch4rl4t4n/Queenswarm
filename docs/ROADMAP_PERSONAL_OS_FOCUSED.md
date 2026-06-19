# Personal OS Roadmap — Focused (post Gumroad purge)

> **Updated:** 2026-06-05  
> **Scope:** queenswarm.love solo operator daily stack. Gumroad / MK6 / export-batch **removed** — do not re-add.

**Canonical execution plan (read first):** [`docs/OPERATOR_TRUTH_ROADMAP.md`](OPERATOR_TRUTH_ROADMAP.md) — ST1–ST8 sprint packages · daily stack · audit tiers · AR1–AR6 anti-drift.

Full historical backlog: [`docs/ROADMAP.md`](ROADMAP.md) — POS-ARCH · POS-STAB · POS-* waves (reference only).

**Setup guides:** [`JARVIS_PERSONAL_ADVISOR_SETUP.md`](JARVIS_PERSONAL_ADVISOR_SETUP.md) · [`COMMUNITY_ENGAGEMENT_SETUP.md`](COMMUNITY_ENGAGEMENT_SETUP.md)

---

## Four layers (never confuse again)

| Layer | Meaning | Trust |
|-------|---------|-------|
| **L1 Platform** | Shipped code (Jarvis, lanes, foragers, CE, compound) | Use daily |
| **L2 Discipline** | ST1 — OP1 · MM8 · LN1 | ✅ discipline gate PASS |
| **L3 Adoption** | ST4–ST7 — config · procedures · UX | ✅ ST1–ST7 PASS (2026-06-19) |
| **L4 Optional** | ST8 — voice · Reddit live · Slack · Track M | ✅ shipped (opt-in scripts) |

**Rule:** L1 at 100 % + L2 red = **partial**, not AFK-trust. Solo-readiness was capped at **84 % / partial** until ST1 PASS — now reflects checklist when discipline gate is green.

---

## Daily stack (L1 — use today)

| Step | Route | Module |
|------|-------|--------|
| Morning triage | `/tasks` | Jarvis strip · Kanban |
| Delegate | `/agents` | Sessions · four-lane digests |
| Intel | `/foragers` · `/knowledge` | Social Intel · CE forager · Brain Pack |
| Lanes | `/agentic-os#lanes` | Digest inbox → promote |
| Approvals | Approval Inbox · publish queue | J3 email · compound drafts |
| Evening | `/ballroom` | Dump & Sleep |

---

## Sprint packages (what to build next)

| Sprint | Merges | Priority | Exit |
|--------|--------|----------|------|
| **ST1** | OP1 · MM8 · LN1 | ✅ P0 | `audit-personal-os-discipline-gate.sh` PASS |
| **ST2** | OP2 · OP3 · LN2 | ✅ P0 | `audit-personal-os-st2-gate.sh` PASS |
| **ST3** | OP4 tech_scv | ✅ P0 | `audit-personal-os-st3-gate.sh` · 3 IL proposals |
| **ST4** | CE/JAR ops · JA2 · OP5/6 | ✅ P1 | `audit-personal-os-st4-gate.sh` PASS |
| **ST5** | HN1–3 · MM7 · CE5 · JA3–4 | ✅ P1 | `audit-personal-os-procedures-gate.sh` PASS |
| **ST6** | HN4/JA6 · LN3/5 · CE7/8 | ✅ P2 | Mission Home strategic/AFK strips |
| **ST7** | HN5/JA5 · MM9–10 | ✅ P2 | `personal_os_eval_metrics_service` |
| **ST8** | CE6 · JA7 · OP7–9 · HN6 · Track M | ✅ P3 | `audit-personal-os-st8-gate.sh` PASS |

**Freeze lifted (ST1–ST7 green):** new Mission Home strips still require **AR3** demotion · new POS-* waves require **AR2** (one entry per sprint).

---

## Shipped modules (reference)

### POS-JAR — Jarvis / personal advisor

| ID | What | Status |
|----|------|--------|
| Shipped | H1 Jarvis · I2 nudge · I3 · J1 · J3 · PA2 | ✅ |
| JA1 | Skill `personal-advisor-playbook` | ✅ |
| JA2 | Curated MISSION/IDEAL_STATE seeded | ✅ |
| JA3–JA4 | Procedures `/advisor` · `/advisor-eval` | ✅ ST5 |
| JA5–JA7 | → ST7 · ST8 | ST7 ✅ · JA7 voice prep ✅ |

### POS-CE — community engagement

| ID | What | Status |
|----|------|--------|
| CE1–CE4 | Skill · wizard · seed · lane caps | ✅ |
| CE5–CE8 | Procedures · Mission Home UX | ✅ ST5–ST6 |
| CE6 Reddit live | → ST8 | ✅ policy + cap (default off) |

```bash
./scripts/audit-community-engagement-gate.sh
./scripts/operator-community-engagement-provision.sh
```

---

## Anti-drift (AR1–AR6)

| ID | Rule |
|----|------|
| AR1 | Readiness cannot be `ready` without discipline gate PASS |
| AR2 | Max **one** new operator entry per sprint |
| AR3 | New Mission Home strip → demote one to Advanced |
| AR4 | No new POS-* wave until ST1 PASS (✅ lifted — use AR2 per sprint) |
| AR5 | POS-ARCH AG1–AG5 on every feature |
| AR6 | Weekly `./scripts/audit-personal-os-truth-gate.sh` |

---

## Deferred ⏸

Memory Manager · repo MEMORY.md · Jarvis Core module · n8n primary · Reddit autopilot · Agent Template System · new strips without AR3

---

## Operator audits

```bash
# L2 core (discipline + ST2–ST4)
./scripts/audit-personal-os-truth-gate.sh

# Full truth + platform (same — ST3/ST4 in L2 section)
./scripts/audit-personal-os-truth-gate.sh

# Readiness (reflects checklist when ST1 discipline PASS)
./scripts/operator-solo-readiness-audit.sh

# Weekly ritual (core blocks, adoption warns)
./scripts/operator-personal-os-verify.sh

# ST1–ST7 closure snapshot (gates + human backlog)
./scripts/operator-personal-os-signoff.sh
```

Maintenance cadence: [`docs/PERSONAL_OS_MAINTENANCE.md`](PERSONAL_OS_MAINTENANCE.md)
