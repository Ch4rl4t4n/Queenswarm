# Operator quickstart — 3 human steps to launch

Dev backlog **100% complete**. Automated gates **green**. Three operator actions remain.

```bash
./scripts/operator-next.sh
./scripts/operator-pending-status.sh | jq .
```

---

## Step 1 — Hetzner email (~5 min)

```bash
./scripts/operator-hetzner-copy-email.sh
```

| Field | Value |
|-------|--------|
| To | `abuse@hetzner.com` |
| Subject | `Re: AbuseID 11B0286:23 — remediation completed` |
| Body | Full output from script |

After send:

```bash
./scripts/operator-mark-hetzner-sent.sh
```

Guide: `docs/OPERATOR_HETZNER_SEND.md`

---

## Step 2 — Stripe Dashboard (~20 min)

```bash
./scripts/operator-stripe-dashboard-checklist.sh
```

1. [API keys](https://dashboard.stripe.com/apikeys) → `STRIPE_SECRET_KEY=sk_live_...`
2. [Products](https://dashboard.stripe.com/products) → Pro €29/mo → `STRIPE_PRO_PRICE_ID`
3. [Webhooks](https://dashboard.stripe.com/webhooks) → `https://queenswarm.love/api/v1/billing/stripe/webhook` → `checkout.session.completed` → `STRIPE_WEBHOOK_SECRET=whsec_...`

Add to `.env.prod`, then:

```bash
./scripts/operator-p0-close.sh
```

Guide: `docs/OPERATOR_STRIPE_DASHBOARD_WALKTHROUGH.md`

---

## Step 3 — Verify launch (~10 min)

```bash
./scripts/operator-post-p0-verify.sh
```

Browser smoke:

- `https://queenswarm.love/settings/billing` → Upgrade Pro
- `https://queenswarm.love/integrations?tab=skills` → Premium unlock

Optional harness (post-launch):

```bash
./scripts/operator-github-webhook-prep.sh
./scripts/operator-harness-env-prep.sh
ENV_FILE=.env.prod ./scripts/deploy-prod.sh
```

---

## One command — full prep status

```bash
./scripts/operator-p0-prep-all.sh
```

## References

- `docs/OPERATOR_LAUNCH_INDEX.md`
- `docs/OPERATOR_P0_CLOSE.md`
