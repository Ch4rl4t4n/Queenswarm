# Authenticated production walkthrough

Operator checklist for **queenswarm.love** — login through supervisor session approve + playbook save.

Run the automated slice first:

```bash
PLAYWRIGHT_BASE_URL=https://queenswarm.love ./scripts/prod-walkthrough-gate.sh

# Optional: mint dashboard:proxy JWT on prod host for automated cockpit smoke
docker compose -p queenswarm_prod exec backend python scripts/issue_dashboard_jwt.py
OPERATOR_BEARER_TOKEN=<token> SKIP_E2E=1 ./scripts/prod-walkthrough-gate.sh

# User JWT: auto-minted from prod backend when reachable (first active admin), or paste browser token:
docker compose -p queenswarm_prod exec backend python scripts/issue_operator_user_jwt.py
OPERATOR_USER_BEARER_TOKEN=<user-jwt> SKIP_E2E=1 ./scripts/prod-walkthrough-gate.sh
```

## 1 — Login & shell

- [ ] Open `https://queenswarm.love/login` — no horizontal overflow on mobile
- [ ] Sign in with admin/operator account — lands on Queen Dashboard `/`
- [ ] Sidebar (desktop) or bottom nav (mobile) — all 6 hubs reachable
- [ ] Command Center (Settings → Command Center) — disk ~10%, memory sane, 10 prod containers

## 2 — Create supervisor session

- [ ] Go to **Agents** → **Sessions** tab
- [ ] **New session** — goal e.g. “Verify checkout latency playbook”
- [ ] Roles / retrieval contract accepted — session row appears with `needs_input` or `running`
- [ ] Open session drawer — sub-agents listed, event log loads without crash

## 3 — Interact

- [ ] **Interact** — send refinement command to sub-agents
- [ ] Drawer stays open; no duplicate auto-reopen after Close
- [ ] Degraded sync banner visible only when API mock/live mismatch (should be absent on prod)

## 4 — Approve

- [ ] **Approve** (or review with decision approve) on session in `needs_input`
- [ ] Status transitions — toast confirms review
- [ ] If **auto-save playbook** enabled (Settings → Audit → Session playbook automation): toast mentions recipe auto-saved

## 5 — Playbook

- [ ] **Save playbook** from drawer → preview modal shows suggested name + steps
- [ ] Confirm save — recipe appears under **Knowledge** / Recipes (topic tags include `operator_playbook`)
- [ ] Optional: export skill from recipe catalog

## 6 — Operator tooling (spot check)

- [ ] Settings → **Audit** — digest config saves; test webhook if configured
- [ ] Session **audit** tab in drawer — fanout events listed
- [ ] **Playbook automation** toggle persists after reload

## 7 — Phase 0 commercial (Swarm Builder + billing)

- [ ] `/swarms/new` — Exec Assistant template loads, review step shows 3 agents
- [ ] `/swarms/new?template=lead-waterfall` — Lead Waterfall review (3 bees + routine)
- [ ] `/swarms/new?template=content-flywheel` — Content Flywheel review
- [ ] Commercial Free tenant — Pro upgrade banner on wizard + `/settings/billing`
- [ ] `/settings/billing` — plan comparison shows agents/swarms limits (Free: 2/1)
- [ ] After Stripe keys: **Upgrade to Pro** starts checkout (not disabled)

## 8 — Phase 1 stickiness (dashboard widgets)

- [ ] `/dashboard` — Rapid learning loop widget shows SLA (or „warming“)
- [ ] `/dashboard` — Time saved ROI panel loads (hours saved breakdown)
- [ ] `/dashboard` — Lead magnets share card + copy link works
- [ ] `/magnet/exec-assistant` — public landing loads (no login)
- [ ] `/magnet/lead-waterfall` — public landing loads (200)
- [ ] `/magnet/content-flywheel` — public landing loads (200)
- [ ] `/leaderboard` — Bee badges panel visible (Pro/internal)

## 9 — Phase 2 enterprise + performance

- [ ] `/settings/enterprise` — white-label, compliance export, HA/DR drill card
- [ ] Latest DR drill JSON visible in Enterprise panel (after `./scripts/dr-drill.sh`)
- [ ] After quarterly `./scripts/ha-chaos-smoke.sh` — HA chaos evidence card shows pass/fail
- [ ] Commercial Pro tenant — **Upgrade to Enterprise** on `/settings/billing` (not disabled after Stripe keys)
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
| Pro billing CTA | | |
| Enterprise billing CTA | | |
| Time saved ROI | | hours: |
| Lead magnet | | template_id: |
| DR drill evidence | | file: |
| Enterprise panel | | |
| Cockpit bundle | | agents: |
| Virtual roster | | |

## Rollback / blockers

| Blocker | Action |
|---------|--------|
| Stripe checkout | P0 — keys in `.env.prod` |
| 401 on all API | Refresh session / check `SECRET_KEY` |
| Session drawer crash | Check browser console; file issue with session_id |

See also: [PRODUCTION_SIGNOFF.md](./PRODUCTION_SIGNOFF.md), [OPERATOR_AUDIT.md](./OPERATOR_AUDIT.md).
