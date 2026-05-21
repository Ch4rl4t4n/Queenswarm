# Operator P0 — Close checklist

Last automated run: see `reports/operator/OPERATOR_SIGNOFF_*.md`

## Status

| Track | Status |
|-------|--------|
| Dev Phase 0–2 + perf | ✅ Complete |
| Automated walkthrough (API + browser + session + command center) | ✅ `operator-launch-gate.sh` |
| HA/DR + host exposure | ✅ Evidence on disk |
| Disk | ✅ ~10% after build cache prune |
| **Stripe live checkout** | ⏳ **Blocked — empty keys in `.env.prod`** |
| **Hetzner abuse email** | ⏳ Draft ready — operator must send |

## One command after Stripe keys

```bash
# 1. Add to .env.prod:
#    STRIPE_SECRET_KEY=sk_live_...
#    STRIPE_WEBHOOK_SECRET=whsec_...

./scripts/operator-stripe-prep.sh       # must show READY
./scripts/operator-p0-close.sh        # deploy + verify + handoff
```

## Hetzner (manual)

```bash
./scripts/operator-hetzner-send-prep.sh
# Send reports/hetzner/hetzner-reply-*.txt → abuse@hetzner.com
# Subject: Re: AbuseID 11B0286:23 — remediation completed
```

## Stripe CLI (optional)

```bash
./scripts/operator-stripe-login.sh
```

## Re-run automated evidence only

```bash
SKIP_E2E=1 SKIP_RESPONSIVE_E2E=1 ./scripts/operator-final-handoff.sh
```

## References

- `docs/TOMORROW_OPERATOR_RUNBOOK.md`
- `docs/AUTHENTICATED_PROD_WALKTHROUGH.md`
- `docs/MISSION_EXECUTION_BACKLOG.md`
