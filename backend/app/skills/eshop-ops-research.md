---
name: eshop-ops-research
description: Researches e-commerce opportunities — products, pricing, listings, competitor shops. Use when e-shop swarm needs product intel before Shopify/Woo sync — NOT for payment processing (use stripe-checkout-webhooks).
version: 1.0.0
priority: 78
roles: [researcher, designer]
keywords: [eshop, ecommerce, shopify, woocommerce, product, listing, pricing, inventory]
source: queenswarm.love
---

# E-shop Ops Research

Purpose: Product research pipeline before storefront connectors go live.

## Workflow

1. **Niche scan** — Apify + competitor-scrape-analyze
2. **Product hypotheses** — margin, demand signals, differentiation
3. **Listing draft** — title, SEO, bullets, A/B variants
4. **Notion backlog** — prioritized SKU candidates
5. **Social teaser** — simulate publish to validate hooks
6. **HiveMind** — verified insights → recipes

## Future connectors (planned)

- Shopify Admin API
- WooCommerce REST
- Stripe Checkout webhooks
- GA4 conversion events

## Guardrails

- No inventory commits without operator approval
- Simulate publish for all social teasers
- Price changes require critic review
