# Operator — Stripe live checkout setup

Blocked until live keys are in `.env.prod`. No secrets are stored in this repo.

## Quick status

**Detailed walkthrough:** `docs/OPERATOR_STRIPE_DASHBOARD_WALKTHROUGH.md`

```bash
./scripts/operator-stripe-dashboard-checklist.sh
./scripts/operator-stripe-prep.sh
```

## 1. Stripe Dashboard — API keys

1. [Stripe Dashboard](https://dashboard.stripe.com) → **Developers → API keys**
2. Copy **Secret key** (`sk_live_...`) → `.env.prod`:

```bash
STRIPE_SECRET_KEY=sk_live_...
```

## 2. Products & prices

Create (or reuse) subscription products:

| Plan | Suggested price | Env var |
|------|-----------------|---------|
| Pro | €29/mo | `STRIPE_PRO_PRICE_ID=price_...` |
| Enterprise | €99/mo | `STRIPE_ENTERPRISE_PRICE_ID=price_...` |

**Fallback** if price IDs unset:

```bash
STRIPE_PRO_PRICE_EUR_CENTS=2900
STRIPE_ENTERPRISE_PRICE_EUR_CENTS=9900
```

## 3. Webhook endpoint

**Developers → Webhooks → Add endpoint**

| Field | Value |
|-------|--------|
| URL | `https://queenswarm.love/api/v1/billing/stripe/webhook` |
| Events | `checkout.session.completed` |

Copy **Signing secret** (`whsec_...`) → `.env.prod`:

```bash
STRIPE_WEBHOOK_SECRET=whsec_...
```

## 4. Full `.env.prod` block (example)

```bash
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
STRIPE_ENTERPRISE_PRICE_ID=price_...
# Optional fallbacks:
# STRIPE_PRO_PRICE_EUR_CENTS=2900
# STRIPE_ENTERPRISE_PRICE_EUR_CENTS=9900
```

## 5. Deploy + verify

```bash
./scripts/operator-stripe-prep.sh          # must show READY
./scripts/operator-p0-close.sh             # deploy + verify + handoff
# or manually:
./scripts/finish-stripe-setup.sh
./scripts/verify-stripe-live.sh
```

## 6. Test checkout (after deploy)

1. Log in to `https://queenswarm.love`
2. **Settings → Billing** → upgrade to Pro
3. Complete Stripe Checkout (test card in test mode, live card in live mode)
4. Confirm webhook delivery in Stripe Dashboard → Webhooks → Recent events

## 7. Stripe CLI (optional local webhook forward)

```bash
./scripts/operator-stripe-login.sh
stripe listen --forward-to https://queenswarm.love/api/v1/billing/stripe/webhook
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `operator-stripe-prep` BLOCKED | Add `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` |
| Webhook 4xx | Check `STRIPE_WEBHOOK_SECRET` matches Dashboard signing secret |
| Checkout URL missing | Redeploy after keys: `ENV_FILE=.env.prod ./scripts/deploy-prod.sh` |
| 402 on skill export | Expected until checkout completes or Pro tier active |

## References

- `docs/OPERATOR_P0_CLOSE.md`
- `scripts/finish-stripe-setup.sh`
- `scripts/verify-stripe-live.sh`
