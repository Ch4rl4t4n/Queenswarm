# Queenswarm — Frontend agent harness

Parent: [`../AGENTS.md`](../AGENTS.md)

## Stack

Next.js 15 App Router · TypeScript strict · Tailwind v4 · shadcn/ui (bee-hive neon-dark theme)

## Rules

- Server Components by default; `"use client"` only when needed
- Named exports (except `page.tsx` / `layout.tsx`)
- API via `frontend/lib/api.ts`; no inline styles
- Loading skeletons + route `error.tsx` boundaries
- Desktop (≥1024px): sidebar + canvas only — no duplicate top search bar (`max-lg:` / mobile tablet scopes)

## Design tokens

- Background `#050510` · Pollen `#FFB800` · Cyan `#00FFFF` · Success `#00FF88`
- Headings: Space Grotesk · Data: JetBrains Mono

## Key paths

| Concern | Location |
|---------|----------|
| Dashboard shell | `app/(dashboard)/` |
| Harness panel | `components/hive/settings-harness-panel.tsx` |
| Tool Hub | `components/connectors/unified-tool-hub-panel.tsx` |
| Breakpoints | `lib/breakpoints.ts` |

## Testing

```bash
cd frontend && npm run typecheck && npm run test
```

Responsive shell E2E: `e2e/responsive-shell.spec.ts`
