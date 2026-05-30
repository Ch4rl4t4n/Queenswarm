---
name: seo-audit-playbook
description: Runs structured SEO audits on public pages and competitor SERPs. Use when optimizing e-shop or marketing landing pages — NOT for authenticated admin panels.
version: 1.0.0
priority: 76
roles: [researcher, browser_operator]
keywords: [seo, audit, serp, landing, meta, sitemap, marketing]
source: queenswarm.love
---

# SEO Audit Playbook

Purpose: Automated SEO findings → Notion backlog → optional publish fixes (simulate).

## Workflow

1. Crawl target URLs (browser harness / Apify)
2. Check: title, meta, H1, canonical, Core Web Vitals hints
3. Compare competitor SERP snippets (public only)
4. Output prioritized fix list with evidence
5. HiveMind verify before ingest

## Output

- Critical / high / low issues
- Suggested copy changes (draft only)
- No live CMS publish without approval gate
