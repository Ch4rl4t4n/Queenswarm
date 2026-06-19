# Jarvis / Personal Advisor — setup (POS-JAR)

**Goal:** Jarvis-like life/business coach **inside** Queenswarm — not a separate Python app, n8n flow, or `memory/` folder.

Pattern sources: Peter Yang (4-file coach) · Chris Harris (layered context) · Nate B Jones (delegation loop) — **adapted with verify-first + tenant memory**.

**Roadmap:** POS-JAR in [`ROADMAP.md`](ROADMAP.md) · stack POS-H · POS-I · POS-J · POS-MEM · POS-HN

---

## What you already have (don't rebuild)

| Video promise | Queenswarm (shipped) |
|---------------|---------------------|
| Daily coach steps | **POS-H1** Jarvis strip — Mission Home max 3 steps |
| Plan / goals | Curated **MISSION** + **IDEAL_STATE** + solo daily plan |
| Learnings memory | INSTRUCTIONS distill · episodic · **J1** weekly compound gardener |
| Eval / self-check | **H6** agent quality scorecard · closed review · Grok gate |
| Proactive nudge | **I2** Jarvis mission feed |
| Weekly reflection | **I3** Ballroom + episodic strip |
| Calendar-aware | **PA2** Life OS Google Calendar in daily plan |
| Email coach loop | **J3** Gmail read-only → simulate drafts → Approval Inbox |
| Research delegation | **H3** Research Bee project batch URLs |
| AFK execution | Four-lane + Celery durable sessions |
| Voice Jarvis | Optional infra — **not** Personal OS P0 |

---

## Architecture (better than video stacks)

```
Curated PLAN (MISSION/IDEAL_STATE)
        ↓
Jarvis strip (3 verify-first steps)  ← Mission Home /tasks
        ↓
Delegate → supervisor session | four-lane | /loop
        ↓
Eval (scorecard + rubric + critic APPROVE)
        ↓
Learnings → INSTRUCTIONS (MM8 gate) · J1 weekly compound
```

**Moat vs videos:** simulate-first · HITL approval inbox · no git memory rot · one app surface.

---

## Quick start (operator)

### 1. Curated memory — your `plan.md` equivalent

**Knowledge → Curated memory**

| Kind | Content (example) |
|------|-------------------|
| **MISSION** | 12-month outcomes (business + life) |
| **IDEAL_STATE** | Weekly energy, principles, non-goals |
| **SOUL** | Tone: direct, verify-first, no hype |
| **INSTRUCTIONS** | Operating rules + distilled learnings |

Run weekly: Settings → memory evolution proposals (J1 gardener, Sundays UTC).

### 2. Daily loop (10 min morning)

1. Open **`/tasks`** — Jarvis strip (3 steps)
2. Clear **Approval Inbox** (email drafts, compound proposals — K2)
3. Check **Life OS** calendar strip
4. Delegate heavy work: **Agents → New session** with skill `personal-advisor-playbook` or four-lane digest

Evening: **`/ballroom`** Dump & Sleep.

### 3. Eval ritual (weekly, 5 min)

- Mission Home **Agent Quality** scorecard (H6)
- `./scripts/audit-jarvis-intelligence-gate.sh`
- When shipped: **HN5** eval dashboard + **MM7** `/memory-review`

### 4. Delegation (Nate B Jones pattern)

Don't chat-loop execution. From Jarvis step → launch:

| Work type | Delegate to |
|-----------|-------------|
| Code / PR | Tech SCV lane or Maintainer |
| Marketing | marketing_najman digest |
| Research | Research Bee project |
| Complex build | `/loop` procedure (LN3, when shipped) |
| Community replies | POS-CE community playbook |

---

## Combine with ✅

Operator Loop · POS-CE community · Social Intel (inbound) · Goldmine alerts · Brain Pack · Recipe Library

## Do not combine ❌

Separate Jarvis Core module · repo `memory/*.md` · n8n primary orchestration · autopilot email send · trading cockpit in Personal OS

---

## Roadmap — POS-JAR (remaining)

| ID | Item | Priority |
|----|------|----------|
| JA1 | Skill `personal-advisor-playbook` | ✅ |
| JA2 | Operator PLAN template in curated bundle (seed doc) | ⏳ P1 config |
| JA3 | Procedure **`/advisor`** → Jarvis + session delegate | ⏳ P2 HN1 |
| JA4 | Procedure **`/advisor-eval`** — checklist + scorecard link | ⏳ P2 |
| JA5 | **Coach compound ritual** doc — J1 + MM7 + HN5 one weekly flow | ⏳ P2 |
| JA6 | HN4 Mission Home Strategic vs AFK = Jarvis UI split | ⏳ P2 |
| JA7 | Voice interface (ElevenLabs/LiveKit) | ⏳ P3 optional |

---

## Verification

```bash
./scripts/audit-jarvis-intelligence-gate.sh
./scripts/operator-personal-os-verify.sh
./scripts/operator-solo-readiness-audit.sh
```

- [ ] Jarvis strip shows on `/tasks`
- [ ] MISSION + IDEAL_STATE non-empty
- [ ] Dump & Sleep ran this week
- [ ] No AFK auto-approve on critic fail (OP1)

---

## Related

- [`OPERATOR_LOOP_MANUAL.md`](OPERATOR_LOOP_MANUAL.md)
- [`PERSONAL_OS_MAINTENANCE.md`](PERSONAL_OS_MAINTENANCE.md)
- [`COMMUNITY_ENGAGEMENT_SETUP.md`](COMMUNITY_ENGAGEMENT_SETUP.md)
