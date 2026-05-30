---
name: stripe-checkout-webhooks
description: Handles Stripe Checkout Sessions, PaymentIntents, and webhook-verified payment events. Use when e-shop payments or order sync — NOT for raw card data or live capture without real-money-risk-gate.
version: 1.0.0
priority: 88
roles: [orchestrator, coder, critic]
keywords: [stripe, checkout, webhook, payment, ecommerce, financial, order]
source: queenswarm.love
reference_mode: true
references: https://docs.stripe.com/webhooks
---

# Stripe Checkout & Webhooks

Purpose: **Checkout Sessions** for e-shop + **webhook-verified** payment events.

## Architecture

- **Outbound**: `stripe_rest_api` connector (Checkout Session, PaymentIntent create)
- **Inbound**: `POST /api/v1/commerce/webhooks/stripe` (signature verified, no JWT)

## Workflow

1. Create Checkout Session in **simulate** mode first
2. Operator approves live via real-money-risk-gate
3. Configure Stripe webhook → Queenswarm endpoint
4. On `checkout.session.completed` → queue HiveMind order ingest
5. Audit log every financial event

## Env

- `COMMERCE_WEBHOOKS_ENABLED=true`
- `STRIPE_WEBHOOK_SECRET=whsec_...` (from Stripe dashboard)

## Guardrails

- Never store card numbers in HiveMind or logs
- Webhook idempotency by `event_id`
- Refunds require operator approval
