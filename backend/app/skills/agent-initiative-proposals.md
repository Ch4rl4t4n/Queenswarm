---
version: "1.0"
priority: 0.86
roles:
  - supervisor
  - critic
  - researcher
keywords:
  - initiative
  - self-proposed improvements
  - suggestions
  - approval workflow
  - guardrails
---

# Agent Initiative Proposals

Use this skill when an agent should proactively propose improvements after reflection.

## Proposal categories

1. New skill proposal.
2. Workflow optimization.
3. Prompt optimization.
4. Tooling fallback proposal.

## Safety policy

- Low-risk prompt/workflow/skill proposals may be auto-approved.
- Medium/high-risk suggestions always require supervisor approval.
- Any proposal touching destructive operations, production secrets, privileged execution, or unsafe tooling must stay pending.

## Expected output

- A concise title and rationale.
- Risk level + impact estimate.
- Clear approval recommendation.
