# Production sign-off — Queenswarm

Checklist before declaring a rollout complete on `queenswarm.love`.

## Automated gate

```bash
# Full gate (local pytest + prod E2E)
PLAYWRIGHT_BASE_URL=https://queenswarm.love ./scripts/production-signoff-gate.sh

# After Stripe keys are in .env.prod
STRICT_STRIPE=1 PLAYWRIGHT_BASE_URL=https://queenswarm.love ./scripts/production-signoff-gate.sh
```

The gate runs: `validate-prod-env` → `core-reliability-gate` → backend pytest → responsive/PWA E2E → edge smoke → Stripe readiness.

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

- [ ] `/integrations` → Skills tab: banner when Stripe off; checkout disabled gracefully
- [ ] Foragers API returns 401 without JWT (not 404)
- [ ] Paper trading summary returns 401 without JWT (not 404)

### Stripe (when keys configured)

1. Add to `.env.prod`:
   - `STRIPE_SECRET_KEY`
   - `STRIPE_WEBHOOK_SECRET`
2. Stripe Dashboard → Webhooks → `https://queenswarm.love/api/v1/billing/stripe/webhook`
   - Event: `checkout.session.completed`
3. Redeploy: `POST_DEPLOY_HEALTH=1 ./scripts/deploy-prod.sh`
4. Verify: `./scripts/stripe-prod-setup.sh` exits 0
5. Complete one premium skill checkout end-to-end

## Known blockers

| Item | Status |
|------|--------|
| Stripe keys in `.env.prod` | Required for live checkout |
| Backend coverage 80% | Backlog (CI gate at 50%) |

## Rollback

```bash
./scripts/rollback.sh
```
