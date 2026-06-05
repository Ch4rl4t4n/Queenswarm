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
  not_verified: "Not verified — approve forge first",
};

export type LibrarySieveVerdict = "launch" | "worth_retry" | "deprioritize" | "retire" | "all";

export const LIBRARY_SIEVE_LABELS: Record<Exclude<LibrarySieveVerdict, "all">, string> = {
  launch: "Launch ready",
  worth_retry: "Fix & retry",
  deprioritize: "Deprioritize",
  retire: "Retire candidate",
};

export function verdictTone(
  verdict: string | null | undefined,
): "ok" | "warn" | "err" | "info" | "purple" | "gold" {
  if (verdict === "launch") return "ok";
  if (verdict === "worth_retry") return "info";
  if (verdict === "deprioritize") return "warn";
  if (verdict === "retire") return "err";
  return "warn";
}

export function sellableIssueLabel(code: string): string {
  return LABELS[code] ?? code.replaceAll("_", " ");
}
