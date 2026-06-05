/** Default Eval-as-a-Service sample — passes heuristic Run eval (no LLM critic). */

export const HARNESS_EVAL_DEFAULT_TITLE = "Eval-as-a-Service — Gumroad workflow pack";

export const HARNESS_EVAL_DEFAULT_MARKDOWN = `---
name: eval-as-a-service-workflow
description: Evaluates agent SKILL.md packs for Gumroad launch readiness. Use when shipping harness bundles — NOT for unstructured chat prompts.
version: 1.0.0
priority: 80
roles: [critic, orchestrator, researcher]
keywords: [eval, harness, gumroad, skill-factory, quality-gate, workflow]
source: queenswarm.love
---

# Eval-as-a-Service Workflow

Purpose: Turn SKILL/workflow markdown into a PASS/FAIL EVAL_REPORT buyers can trust.

## When to use

- Before listing a harness pack on Gumroad (~€29)
- After Skill Factory forge when quality/critic badges are unclear
- When onboarding a client workflow into Queenswarm Library

## When NOT to use

- Unstructured one-off chat prompts without YAML frontmatter
- Live trading, billing, or publish actions without approval gates

## Workflow

1. **Ingest** — Collect SKILL.md (frontmatter + body) and optional HARNESS.md context.
2. **Structure check** — Validate name, description, heading, 3+ steps, and guardrails.
3. **Simulate** — Dry-run workflow steps; never publish unverified outputs to production.
4. **Critic verdict** — APPROVE only when structure passes and evidence is cited.
5. **Report** — Emit EVAL_REPORT.md with tier, score, issues, and Gumroad price hint.

## Output format

- Tier: sellable | draft | rejected
- Score: 0.00–1.00 with issue bullets
- Critic verdict line: APPROVE or REJECT
- Recommended Gumroad price in EUR cents

## Guardrails

- Never APPROVE generic skill-factory-output fallback templates.
- Strip secrets and PII before sending markdown to external LLM critics.
- Human operator approves Gumroad publish — eval is advisory only.
- Sandbox all code execution; simulate-first before customer delivery.

## Verification checklist

- [ ] Frontmatter name and description present
- [ ] At least three numbered workflow steps
- [ ] When to use or guardrails section present
- [ ] Critic line ends with APPROVE or REJECT
- [ ] EVAL_REPORT downloadable after Run eval
`;
