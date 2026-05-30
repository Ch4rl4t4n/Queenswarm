---
name: research-to-pr-proposal
description: Converts verified research into Innovation Lab proposals and Queen Maintainer PR plans. Use when forager scan, Research Bee, or Innovation Lab brainstorm should become an implementable change — NOT for raw HiveMind dumps without verify.
version: 1.0.0
priority: 92
roles: [researcher, orchestrator, coder, critic]
keywords: [research, innovation, maintainer, pr, proposal, implement, forager, verify]
source: queenswarm.love
reference_mode: true
references: docs/harness/QUEEN_MAINTAINER_INSTRUCTIONS.md
---

# Research → PR Proposal

Purpose: Close the self-improvement loop — **verified research → structured proposal → operator approve → Maintainer PR**.

## Workflow

1. **Ingest** — Research Bee or Forager → HiveMind verify (researcher + critic APPROVED)
2. **Structure** — Innovation Lab proposal:
   - Problem statement
   - Evidence links
   - Tracer bullets (max 7 steps)
   - Risk + rollback
   - Affected modules
3. **Operator review** — approve / reject / needs_input
4. **Queue Maintainer** — `implement_innovation_proposal` (PR-only, branch `queen-maintainer/*`)
5. **Build** — TDD + self-review-loop skills; Cursor/Grok for implementation
6. **Recipe** — save on verified merge

## Proposal template

| Field | Required |
|-------|----------|
| `title` | Yes |
| `problem` | Yes |
| `evidence` | Links + HiveMind refs |
| `tracer_bullets` | 3–7 steps |
| `risk_tier` | read/write/publish/financial |
| `simulation_plan` | Yes |
| `denylist_check` | Pass (no .env, billing, prod compose) |

## Guardrails

- No user-facing report until simulation passes
- Maintainer never writes to `main` directly
- CostGovernor budget respected
