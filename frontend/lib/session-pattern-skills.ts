import type { SupervisorSessionRow } from "@/lib/hive-types";

/** Serialized agentic pattern stack from session ``context_summary``. */
export interface AgenticPatternsSnapshot {
  primary: string[];
  secondary: string[];
  all: string[];
  forced_reflection: boolean;
  resource_aware: boolean;
  rationale: string[];
  router_version: string;
}

export interface SessionPatternSkillsSnapshot {
  patterns: AgenticPatternsSnapshot | null;
  skillsByRole: Record<string, string[]>;
  allSkills: string[];
  suggestedSkills: string[];
  routerEnabled: boolean;
}

function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => String(item).trim()).filter(Boolean);
}

function asStringRecord(value: unknown): Record<string, string[]> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {};
  }
  const out: Record<string, string[]> = {};
  for (const [role, skills] of Object.entries(value as Record<string, unknown>)) {
    const list = asStringList(skills);
    if (list.length > 0) {
      out[role] = list;
    }
  }
  return out;
}

/** Parse ``agentic_patterns`` blob from one session context summary. */
export function parseAgenticPatterns(contextSummary: Record<string, unknown> | null | undefined): AgenticPatternsSnapshot | null {
  const raw = contextSummary?.agentic_patterns;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return null;
  }
  const blob = raw as Record<string, unknown>;
  const primary = asStringList(blob.primary);
  const secondary = asStringList(blob.secondary);
  const mergedAll = asStringList(blob.all);
  const all =
    mergedAll.length > 0
      ? mergedAll
      : [...primary, ...secondary.filter((pid) => !primary.includes(pid))];

  return {
    primary,
    secondary,
    all,
    forced_reflection: Boolean(blob.forced_reflection),
    resource_aware: Boolean(blob.resource_aware),
    rationale: asStringList(blob.rationale),
    router_version: String(blob.router_version ?? "").trim(),
  };
}

function dedupeSkills(items: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const slug of items) {
    if (seen.has(slug)) {
      continue;
    }
    seen.add(slug);
    out.push(slug);
  }
  return out;
}

function skillsFromSubAgents(session: SupervisorSessionRow): Record<string, string[]> {
  const byRole: Record<string, string[]> = {};
  for (const sub of session.sub_agents ?? []) {
    const raw = sub.short_memory?.skills;
    const skills = asStringList(raw);
    if (skills.length > 0) {
      byRole[sub.role] = skills;
    }
  }
  return byRole;
}

/** Aggregate pattern router output and resolved skills for one supervisor session. */
export function extractSessionPatternSkills(session: SupervisorSessionRow): SessionPatternSkillsSnapshot {
  const summary = session.context_summary ?? {};
  const patterns = parseAgenticPatterns(summary);

  const fromSummaryByRole = asStringRecord(summary.resolved_skills_by_role);
  const fromSubAgents = skillsFromSubAgents(session);
  const skillsByRole = Object.keys(fromSummaryByRole).length > 0 ? fromSummaryByRole : fromSubAgents;

  const summarySkills = asStringList(summary.resolved_skill_slugs);
  const flattenedFromRoles = dedupeSkills(Object.values(skillsByRole).flat());
  const allSkills = summarySkills.length > 0 ? summarySkills : flattenedFromRoles;

  const suggestedSkills = asStringList(summary.pattern_suggested_skills);

  return {
    patterns,
    skillsByRole,
    allSkills,
    suggestedSkills,
    routerEnabled: patterns !== null,
  };
}

/** API preview payload from POST /agents/sessions/pattern-preview. */
export interface PatternPreviewPayload {
  router_enabled: boolean;
  agentic_patterns: Record<string, unknown>;
  suggested_skill_slugs: string[];
  pattern_prompt_preview: string;
}

export function patternPreviewToSnapshot(payload: PatternPreviewPayload | null | undefined): SessionPatternSkillsSnapshot {
  if (!payload?.router_enabled) {
    return {
      patterns: null,
      skillsByRole: {},
      allSkills: [],
      suggestedSkills: [],
      routerEnabled: false,
    };
  }
  const patterns = parseAgenticPatterns({ agentic_patterns: payload.agentic_patterns });
  return {
    patterns,
    skillsByRole: {},
    allSkills: [],
    suggestedSkills: asStringList(payload.suggested_skill_slugs),
    routerEnabled: true,
  };
}
