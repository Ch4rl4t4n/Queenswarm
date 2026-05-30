---
name: skill-authoring-template
description: Authors new Queenswarm backend skills compatible with agentskills.io and SkillLibrary. Use when creating or updating SKILL.md files in backend/app/skills — NOT for one-off prompts without persistence.
version: 1.0.0
priority: 75
roles: [orchestrator, coder, researcher]
keywords: [skill, authoring, skillmd, agentskills, template, cursor]
source: queenswarm.love
reference_mode: true
references: https://agentskills.io, https://github.com/addyosmani/agent-skills/blob/HEAD/docs/skill-anatomy.md
---

# Skill Authoring Template

Purpose: Standardize skills for **backend SkillLibrary** + **Cursor `.cursor/skills/`** sync.

## Required frontmatter (Queenswarm + agentskills.io)

```yaml
---
name: kebab-case-slug
description: What it does. Use when [triggers]. NOT for [exclusions].
version: 1.0.0
priority: 50-98
roles: [researcher, coder, critic, orchestrator, designer, browser_operator]
keywords: [token, matching, goal]
source: queenswarm.love
---
```

Optional: `reference_mode: true`, `references: [path or URL]`

## Progressive disclosure (3 layers)

1. **Metadata** — `name` + `description` (always discoverable)
2. **Body** — workflow when skill selected (~600 tokens max in reference mode summary)
3. **References** — heavy docs in `references/` or external URLs (lazy fetch)

## Body sections

1. Purpose (1 sentence)
2. When to use / When NOT
3. Workflow (numbered, max 7 steps)
4. Output format
5. Guardrails
6. Verification checklist

## After create

1. Add keywords for `select_for_task` matching
2. Update `DEFAULT_ROLE_SKILLS` if role-default
3. Export via Recipe → SKILL.md bundle for Cursor install
4. Run `pytest backend/tests/test_supervisor_phase61_unit.py`

## Anti-patterns

- Vague descriptions without "Use when"
- Process steps only in description (agent skips body)
- Duplicating entire docs in body — use reference_mode
