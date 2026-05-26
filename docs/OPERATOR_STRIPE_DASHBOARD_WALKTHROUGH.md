# Stripe Dashboard walkthrough (live mode)

Field-by-field guide for Queenswarm operator P0. **Toggle Live mode** in Stripe Dashboard before copying keys.

## Before you start

```bash
./scripts/operator-stripe-dashboard-checklist.sh
```

---

## Step 1 — Secret API key

1. Open [dashboard.stripe.com/apikeys](https://dashboard.stripe.com/apikeys)
2. Ensure **Live** mode (toggle top-right)
3. Under **Standard keys**, reveal **Secret key**
4. Copy `sk_live_...` → `.env.prod`:

```bash
STRIPE_SECRET_KEY=sk_live_...
```

Do **not** commit this file. Do **not** paste the key in chat or docs.

---

## Step 2 — Product: Queenswarm Pro

1. Open [dashboard.stripe.com/products](https://dashboard.stripe.com/products)
2. **+ Add product**
   - **Name:** `Queenswarm Pro`
   - **Description:** `Pro tier — swarms, integrations, harness dashboard`
3. **Pricing**
   - **Pricing model:** Standard pricing
   - **Price:** `€29.00`
   - **Billing period:** Monthly
   - **Currency:** EUR
4. Save → open the price row → copy **Price ID** (`price_...`)

```bash
STRIPE_PRO_PRICE_ID=price_...
```

**Fallback** (if you skip creating a Dashboard price):

```bash
STRIPE_PRO_PRICE_EUR_CENTS=2900
```

---

## Step 3 — Product: Queenswarm Enterprise (optional at first launch)

Same flow as Pro:

- **Name:** `Queenswarm Enterprise`
- **Price:** `€99.00` / month / EUR

```bash
STRIPE_ENTERPRISE_PRICE_ID=price_...
# or
STRIPE_ENTERPRISE_PRICE_EUR_CENTS=9900
```

---

## Step 4 — Webhook endpoint

1. Open [dashboard.stripe.com/webhooks](https://dashboard.stripe.com/webhooks)
2. **+ Add endpoint**
3. Fill exactly:

| Field | Value |
|-------|--------|
| **Endpoint URL** | `https://queenswarm.love/api/v1/billing/stripe/webhook` |
| **Description** | `Queenswarm billing — checkout.session.completed` |
| **Events** | Select **`checkout.session.completed`** only |
| **API version** | Latest (default) |

4. **Add endpoint** → open the new endpoint → **Reveal** under **Signing secret**
5. Copy `whsec_...` → `.env.prod`:

```bash
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Verify webhook after deploy

- Stripe → Webhooks → your endpoint → **Send test webhook** (or complete a real checkout)
- **Recent deliveries** should show **200** from Queenswarm

---

## Step 5 — Complete `.env.prod` block

```bash
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
STRIPE_ENTERPRISE_PRICE_ID=price_...

# Recommended redirect URLs (defaults work if unset)
STRIPE_PRO_SUCCESS_URL=https://queenswarm.love/settings/billing?upgrade=success
STRIPE_PRO_CANCEL_URL=https://queenswarm.love/settings/billing?upgrade=cancel
STRIPE_ENTERPRISE_SUCCESS_URL=https://queenswarm.love/settings/billing?upgrade=enterprise-success
STRIPE_ENTERPRISE_CANCEL_URL=https://queenswarm.love/settings/billing?upgrade=enterprise-cancel
STRIPE_SKILLS_SUCCESS_URL=https://queenswarm.love/integrations?tab=skills&purchase=success
STRIPE_SKILLS_CANCEL_URL=https://queenswarm.love/integrations?tab=skills&purchase=cancel

SKILL_EXPORT_PREMIUM_ENABLED=true
```

---

## Step 6 — Deploy and automated verify

```bash
./scripts/operator-stripe-prep.sh      # must exit 0
./scripts/operator-p0-close.sh         # deploy + sign-off
./scripts/verify-stripe-live.sh        # API probe: pro_checkout_ready
```

---

## Step 7 — Browser smoke tests

| # | URL | Action | Expected |
|---|-----|--------|----------|
| 1 | `/settings/billing` | Upgrade to **Pro** | Stripe Checkout opens → success redirect |
| 2 | `/integrations?tab=skills` | **Unlock & export** premium skill | Checkout or already unlocked |
| 3 | Stripe Dashboard | Webhooks → Recent deliveries | HTTP **200** |

---

## Test mode vs live mode

| Mode | Secret key prefix | When to use |
|------|-------------------|-------------|
| Test | `sk_test_...` | Local dev only |
| **Live** | `sk_live_...` | **Production** queenswarm.love |

Queenswarm prod expects **live** keys in `.env.prod`.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Checkout button disabled | `./scripts/operator-stripe-prep.sh` → redeploy |
| Webhook 400/401 | `STRIPE_WEBHOOK_SECRET` mismatch — copy from Dashboard again |
| `pro_checkout_ready=false` | Backend not reloaded — `ENV_FILE=.env.prod ./scripts/deploy-prod.sh` |
| 402 on skill export | Normal until checkout completes |

---

## References

- `docs/OPERATOR_STRIPE_SETUP.md`
- `docs/OPERATOR_P0_CLOSE.md`
- `scripts/finish-stripe-setup.sh`
