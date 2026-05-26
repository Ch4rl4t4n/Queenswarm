---
version: 1.0.0
priority: 92
roles:
  - supervisor
  - researcher
  - coder
  - critic
  - browser_operator
keywords:
  - execution studio
  - external apps
  - connectors
  - mcp_invoke
  - codebase
  - queen maintainer
  - pr-only
  - draft simulate live
reference_mode: true
references:
  - /api/v1/execution-studio/manual
---

# Execution Studio — Governed External & Internal Execution

Use when a task requires **real execution** outside pure planning: SaaS APIs, media tools, or **codebase PRs**.

## Manual (always consult)

Fetch the live operator manual before planning execution steps:

- **Full manual:** `GET /api/v1/execution-studio/manual`
- **One section:** `GET /api/v1/execution-studio/manual/{section_id}`

Key sections: `overview`, `execution_modes`, `external_lane`, `internal_codebase`, `research_to_execution`, `agent_reference`.

## Execution modes

| Mode | Use when |
|------|----------|
| **draft** | Plan only — no upstream HTTP, no GitHub |
| **simulate** | Dry-run writes; validate paths and args |
| **live** | Real API calls or open GitHub PR (never merge) |

Default tenant policy is **simulate**. Live writes require operator approval.

## External lane (SaaS, media, routers)

1. Connector must be **installed, credentialed, tested, active**.
2. Invoke via `mcp_invoke` only if connector slug is on manager allowlist.
3. Prefer API connectors (Gmail, Notion, Composio, Nango) over browser.
4. Report to operator only after **simulation** passes.

## Internal lane (codebase / SCV)

1. **Never** edit denylist paths: `.env*`, billing, `docker-compose.prod`, nginx, `config.py`.
2. **Never** commit to main — open PR on `queen-maintainer/*` via `github_rest`.
3. Run tests (pytest/vitest) before proposing PR.
4. Raise **`codebase_execution`** proposal when research suggests repo changes:

```json
{
  "execution_domain": "internal_codebase",
  "goal_excerpt": "<what to change and why>",
  "suggested_paths": ["frontend/components/..."],
  "manual_ref": "/api/v1/execution-studio/manual"
}
```

5. Wait for **operator approval** — handoff triggers Queen Maintainer automatically.

## Research → execution handoff

When optimization research completes:

1. Summarize findings and proposed changes.
2. Create `codebase_execution` initiative or POST `/execution-studio/proposals`.
3. Stop — do not modify repo until operator approves.
4. After approval, Maintainer session runs with your goal injected.

## Output checklist

- Mode used (draft / simulate / live)
- Connectors invoked (slugs + tool names)
- Simulation evidence
- For codebase: PR URL or proposal id — never claim merge without operator confirmation
