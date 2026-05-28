# Frontend — Agent Harness

Next.js 15 App Router · TypeScript strict · Tailwind v4 · shadcn/ui · Framer Motion

## Before editing

1. Read root `AGENTS.md` for philosophy and security
2. Follow `.cursor/rules/queenswarm-core.mdc` responsive rules

## Conventions

- App Router only — never Pages router
- Server Components by default; `"use client"` only when needed
- Named exports (except `page.tsx`, `layout.tsx`)
- Tailwind utilities — no inline styles; use `cn()` from `lib/utils`
- API via `lib/api.ts` (`hiveGet`, `hivePutJson`, …)
- Loading skeletons + error boundaries on routes

## Design system — Bee-Hive Neon-Dark

| Token | Hex | Use |
|-------|-----|-----|
| Background | `#050510` | Deep space |
| Pollen | `#FFB800` | Rewards, success glow |
| Cyan | `#00FFFF` | Active data |
| Magenta | `#FF00AA` | Warnings |
| Green | `#00FF88` | Verified |
| Red | `#FF3366` | Blocked |

**Form spacing:** label → control **6px** (`V4FormField` / `.v4-form-field`); field → field **16px** (`V4FormStack` / `.v4-form-stack`). Labels use `.v4-field-label` (uppercase 11px).

Fonts: Space Grotesk (headings), JetBrains Mono (data/code). Hexagonal cards, glow proportional to value.

## Responsive shell (critical)

Breakpoints: mobile ≤767px, tablet 768–1023px, desktop ≥1024px (`lib/breakpoints.ts`).

**Desktop (≥1024px):** sidebar + canvas only — **never** mount `HiveTopBar` or duplicate search bars.

Use `max-lg:` / `@media (max-width: 767px)` — avoid bare `sm:`/`md:` affecting desktop.

After shell changes: `e2e/responsive-shell.spec.ts`.

## Key routes

| Route | Purpose |
|-------|---------|
| `/` | Redirect → `/cockpit` (CP) or `/dashboard` |
| `/cockpit` | Solo Operator Control Plane home |
| `/dashboard` | Advanced ColonyConsole (legacy Queen dashboard) |
| `/ballroom` | Dump & Sleep upload, swarm chat |
| `/knowledge` | Hive Mind, dreaming, curated memory |
| `/settings/[[...section]]` | Settings keep-alive shell (lazy panels) |
| `/settings/harness` | AI Layer dashboard + behavioral memory |
| `/integrations?tab=studio` | Execution Studio (lazy sub-panels) |

Home route helper: `lib/hive-home-route.ts` (`hiveOverviewHref()`).

Gate: `./scripts/audit-operator-control-plane-gate.sh`

## Testing

```bash
cd frontend && npm run typecheck
cd frontend && npm run test
```

Playwright E2E for user-visible flows.

## Section headers (mandatory)

Every page, card, and tool block: **Title → Description → inline `(i)` hint → content**.

- Page: `HivePageHeader` + `hivePageHintProps()`
- Card: `V4CardHeader` + `hint={sectionHintNode("key")}`
- Nested: `HiveSubsectionHeader` + `hintKey`
- Registry: `lib/section-hints.ts` — add before shipping new UI

See `.cursor/rules/queenswarm-section-headers.mdc` for full rules.

## Platform features

Check `usePlatform().hasFeature()` before rendering gated UI (e.g. `dump_sleep` Pro+).
