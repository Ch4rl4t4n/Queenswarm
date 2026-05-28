# Authenticated production walkthrough

Operator checklist for **queenswarm.love** — login through supervisor session approve + playbook save.

Run the automated slice first:

```bash
# API + route probes (auto dashboard + user JWT)
SKIP_E2E=1 ./scripts/prod-walkthrough-gate.sh

# Prod command center (§1 disk/memory + containers)
./scripts/prod-command-center-gate.sh

# Prod browser shell on queenswarm.love (§1, §7–9 shells)
./scripts/prod-browser-walkthrough-gate.sh

# Prod session API walkthrough (§2–5: create → interact → approve → playbook)
./scripts/prod-session-walkthrough-gate.sh

# All-in-one
SKIP_E2E=1 SKIP_RESPONSIVE_E2E=1 ./scripts/operator-launch-gate.sh
```

## 1 — Login & shell

- [x] ~~Open `https://queenswarm.love/login` — no horizontal overflow on mobile~~ — **automated** (`prod-browser-walkthrough-gate.sh`)
- [ ] Sign in with admin/operator account — lands on Queen Dashboard `/` *(shell routes automated via JWT cookie; full login flow manual)*
- [x] ~~Sidebar (desktop) or bottom nav (mobile) — all 6 hubs reachable~~ — **automated** (authenticated prod Playwright)
- [x] ~~Command Center disk/memory + prod containers~~ — **automated** (`prod-command-center-gate.sh`)

## 2 — Create supervisor session

- [x] ~~Create session via API~~ — **automated** (`prod-session-walkthrough-gate.sh`)
- [ ] **New session** UI flow — goal form, roles contract *(manual browser optional)*

## 3 — Interact

- [x] ~~**Interact** command appended to timeline~~ — **automated** (API)

## 4 — Approve

- [x] ~~**Approve** review decision~~ — **automated** (API)

## 5 — Playbook

- [x] ~~**Save playbook** → recipe in library~~ — **automated** (API; `recipe_id` in JSON report)
- [ ] Optional: export skill from recipe catalog *(manual)*

## 6 — Operator tooling (spot check)

- [ ] Settings → **AI harness** → **Operator Hub** — next action, OAuth readiness, preflight dry-run *(automated: `E2E_OPERATOR_HUB=1` mocked E2E + prod authenticated Playwright)*
- [ ] `./scripts/operator-publish-lane-status.sh` — JSON summary before live enable
- [ ] Settings → **Audit** — digest config saves; test webhook if configured
- [ ] Session **audit** tab in drawer — fanout events listed
- [ ] **Playbook automation** toggle persists after reload

## 7 — Phase 0 commercial (Swarm Builder)

- [x] ~~`/swarms/new` — Exec Assistant template loads~~ — **automated**
- [x] ~~`/swarms/new?template=lead-waterfall` — Lead Waterfall review~~ — **automated**
- [x] ~~`/swarms/new?template=content-flywheel` — Content Flywheel review~~ — **automated**
- [ ] Commercial Free tenant — Pro upgrade banner on wizard

## 8 — Phase 1 stickiness (dashboard widgets)

- [ ] `/dashboard` — Rapid learning loop widget shows SLA (or „warming“)
- [ ] `/dashboard` — Time saved ROI panel loads (hours saved breakdown)
- [ ] `/dashboard` — Lead magnets share card + copy link works
- [x] ~~`/magnet/exec-assistant` — public landing loads (no login)~~ — **automated**
- [x] ~~`/magnet/lead-waterfall` — public landing loads (200)~~ — **automated**
- [x] ~~`/magnet/content-flywheel` — public landing loads (200)~~ — **automated**
- [ ] `/leaderboard` — Bee badges panel visible (Pro/internal)

## 9 — Phase 2 enterprise + performance

- [x] ~~`/settings/enterprise` — white-label, compliance export, HA/DR drill card~~ — **automated** (shell)
- [x] ~~Latest DR drill JSON visible in Enterprise panel~~ — **automated** (API `ha_profile.dr_drill`)
- [x] ~~HA chaos evidence card~~ — **automated** (API `ha_profile.ha_chaos`)
- [ ] After Enterprise checkout: tier shows Enterprise, enterprise workspace unlocked
- [ ] Sidebar brand mark reflects tenant branding (if configured)
- [ ] `/dashboard` — colony loads via cockpit bundle (Network: single `/dashboard/cockpit` on boot)
- [ ] Dashboard list view — agent roster responsive; `/agents` list mode scrolls smoothly at 100+ bees
- [ ] Task queue widget updates without duplicate polls when WS connected (DevTools → fewer `/task-queue` calls)
- [ ] Settings → Capabilities atlas — Phase 2 + perf entries show **live**

## Evidence log (paste into ops notes)

| Step | Pass | Notes |
|------|------|-------|
| Login | | |
| Create session | | session_id: |
| Interact | | |
| Approve | | |
| Playbook save | | recipe_id: |
| Auto-save (if on) | | |
| Swarm Builder | | template: |
| Lead Waterfall magnet | | |
| Time saved ROI | | hours: |
| Lead magnet | | template_id: |
| DR drill evidence | | file: |
| Enterprise panel | | |
| Cockpit bundle | | agents: |
| Virtual roster | | |

## Rollback / blockers

| Blocker | Action |
|---------|--------|
| 401 on all API | Refresh session / check `SECRET_KEY` |
| Session drawer crash | Check browser console; file issue with session_id |

See also: [PRODUCTION_SIGNOFF.md](./PRODUCTION_SIGNOFF.md), [OPERATOR_AUDIT.md](./OPERATOR_AUDIT.md).
