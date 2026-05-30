---
name: competitor-scrape-analyze
description: Scrapes and analyzes public competitor data via browser harness or Apify. Use when market intel, pricing, SEO, or feature comparison is needed — NOT for authenticated private data or PII harvesting.
version: 1.0.0
priority: 80
roles: [researcher, browser_operator]
keywords: [competitor, scrape, apify, browser, intel, pricing, amazon, etsy, seo]
source: queenswarm.love
---

# Competitor Scrape & Analyze

Purpose: Public competitor intelligence → structured brief → HiveMind verify → recipe.

## Tools (priority)

1. **Apify** connector — e-commerce, social, search SERP
2. **Browser harness** (Playwright) — JS-heavy pages, screenshots
3. **Research Bee** — URL paste → structured brief

## Workflow

1. Define competitor set + URLs (operator or forager)
2. Scrape public pages only (robots.txt respect)
3. Extract: pricing, features, messaging, social cadence
4. Synthesize brief with citations
5. HiveMind verify gate before ingest
6. Optional: Innovation Lab proposal for product gaps

## Output format

- Executive summary (3 bullets)
- Comparison table
- Opportunities + risks
- Source URLs with fetch date

## Guardrails

- No login bypass, no paywall circumvention
- Strip PII before logging
- Simulate-first; no auto-publish of scraped content
