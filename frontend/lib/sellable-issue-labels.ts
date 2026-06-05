/** Human labels for Skill Factory sellable issue codes. */

const LABELS: Record<string, string> = {
  critic_not_approved: "Critic must APPROVE — no hedge words",
  needs_3_plus_workflow_steps: "Need 3+ numbered workflow steps",
  forge_quality_gate_failed: "Quality gate failed — fix SKILL.md structure",
  generic_factory_slug: "Slug too generic — tie to niche",
  fallback_skill_frontmatter: "Replace fallback frontmatter",
  factory_draft_description: "Description must be buyer-facing",
  duplicate_niche_suffix: "Differentiate from prior attempt",
  skill_markdown_invalid: "Invalid SKILL.md per agentskills.io",
};

export function sellableIssueLabel(code: string): string {
  return LABELS[code] ?? code.replaceAll("_", " ");
}
