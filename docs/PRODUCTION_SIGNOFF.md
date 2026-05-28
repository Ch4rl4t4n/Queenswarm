# Production sign-off — Queenswarm

Checklist before declaring a rollout complete on `queenswarm.love`.

**Security:** run [PRODUCTION_SECURITY_CHECKLIST.md](./PRODUCTION_SECURITY_CHECKLIST.md) before every production deploy (host exposure audit, Redis auth, firewall).

```bash
./scripts/audit-host-exposure.sh   # fail if data-plane ports listen on 0.0.0.0
```

## Automated gate

```bash
# Full gate (local pytest + prod E2E)
PLAYWRIGHT_BASE_URL=https://queenswarm.love ./scripts/production-signoff-gate.sh
```

Remote hive smoke (``PLAYWRIGHT_BASE_URL``) skips API mocks and runs:

- PWA shell routes
- Public login overflow checks
- Desktop Ballroom FAB visibility
- Desktop sidebar-only shell (no `#hive-search` duplicate)

Local UX tests run with API mocks only.

## Manual QA

### Desktop (≥1024px)

- [ ] Sidebar-only shell — no duplicated top search bar (`#hive-search` hidden)
- [ ] Ballroom FAB visible bottom-right with amber glow (`data-testid="ballroom-fab"`)
- [ ] Hard refresh (`Ctrl+Shift+R`) if FAB missing after deploy
- [ ] PWA install prompt **not** shown on desktop

### Mobile / tablet (<1024px)

- [ ] Bottom nav + drawer; no horizontal overflow on login and dashboard
- [ ] Second visit shows PWA install prompt; dismiss hides for session
- [ ] Airplane mode / offline → offline banner or `/offline` page
- [ ] Safe-area padding on notched devices

### Phase 14 surfaces

- [ ] `/integrations` → Skills tab loads without checkout controls
- [ ] Foragers API returns 401 without JWT (not 404)
- [ ] Paper trading summary returns 401 without JWT (not 404)

## Known blockers

| Item | Status |
|------|--------|
| Backend coverage 80% | **Done** — sign-off gate uses `--cov-fail-under=80` |

## Rollback

```bash
./scripts/rollback.sh
```
