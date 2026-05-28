# Phase 0 — Parallel Agent Split

Updated: 2026-05-21  
Use this when two Cursor agents work the same repo session. **Do not edit the same file in parallel.**

## Status snapshot

| Item | Status | Owner track |
|------|--------|-------------|
| Exec Assistant wizard `/swarms/new` | ✅ Shipped | Agent A |
| Lead Waterfall + Content Flywheel templates | ✅ Shipped | Agent A |
| Pro tier gates + upgrade banner | ✅ Shipped | Agent A |
| Swarm Builder CTA on dashboard | ✅ Shipped | Agent A |
| Capabilities Atlas (live + roadmap) | ✅ Shipped | Agent A |
| Rapid loop dashboard widget | ✅ Shipped + verified | Agent B |
| Dreaming nightly summary card | ✅ Shipped + verified | Agent B |
| Swarm Builder entry on dashboard | ✅ Shipped | Agent B |
| Foragers production launch | ✅ Pro-gated (internal + commercial Pro) | Agent B |
| Built-in plugin persistent toggle | ✅ PATCH + Integrations HiveSwitch | Agent B |
| Authenticated prod walkthrough | ⏳ Manual QA | **You (human)** |

---

## Agent A — DONE (maintenance only)

Wizard track complete.

**Do not re-edit** `swarm-builder-wizard.tsx` unless fixing bugs.

---

## Agent B — DONE (maintenance only)

Dashboard learning loop + integrations verified:

- Rapid loop + dreaming widgets on `/dashboard` (default layout prefs on)
- Foragers enabled in `platform_features.py` + `platform-features.ts` (commercial Pro)
- Plugin PATCH persist wired in `integrations-page-client.tsx`

---

## Shared rules

- Deploy: always `--env-file .env.prod`  
- Before prod deploy: `./scripts/mission-phase0-audit.sh`  
- Bump SW cache in `frontend/public/sw.js` on frontend-only deploys  
- No commits unless user asks  

---

## Human operator

```bash
./scripts/mission-phase0-audit.sh
./scripts/mission-phase1-audit.sh
# Manual: docs/AUTHENTICATED_PROD_WALKTHROUGH.md
```
