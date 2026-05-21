/** Helpers for supervisor session → Recipe Library playbook UI. */

export interface SessionPlaybookPreview {
  session_id: string;
  suggested_name: string;
  step_count: number;
  can_mark_verified: boolean;
  session_status: string;
  sub_agent_count: number;
}

export function parsePlaybookTopicTags(raw: string): string[] {
  const seen = new Set<string>();
  const tags: string[] = [];
  for (const part of raw.split(",")) {
    const tag = part.trim().slice(0, 64);
    if (!tag || seen.has(tag)) {
      continue;
    }
    seen.add(tag);
    tags.push(tag);
    if (tags.length >= 64) {
      break;
    }
  }
  return tags;
}

export function defaultPlaybookTopicTags(): string[] {
  return ["supervisor", "operator_playbook"];
}

export function playbookRecipeIdFromContext(context: Record<string, unknown> | undefined): string | null {
  const raw = context?.playbook_recipe_id;
  if (typeof raw !== "string") {
    return null;
  }
  const trimmed = raw.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function playbookAutoSavedAtFromContext(context: Record<string, unknown> | undefined): string | null {
  const raw = context?.playbook_auto_saved_at;
  if (typeof raw !== "string") {
    return null;
  }
  const trimmed = raw.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function playbookWasAutoSavedOnReview(
  context: Record<string, unknown> | undefined,
  priorRecipeId: string | null,
): boolean {
  const recipeId = playbookRecipeIdFromContext(context);
  if (!recipeId || recipeId === priorRecipeId) {
    return false;
  }
  return playbookAutoSavedAtFromContext(context) !== null;
}
