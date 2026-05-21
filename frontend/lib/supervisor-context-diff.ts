/** Frontend helpers for rendering nested supervisor context diffs. */

export interface SupervisorContextDiffNode {
  added?: Record<string, unknown>;
  removed?: Record<string, unknown>;
  changed?: Record<string, { before: unknown; after: unknown }>;
  nested?: Record<string, SupervisorContextDiffNode>;
  added_items?: unknown[];
  removed_items?: unknown[];
  item_changes?: Array<Record<string, unknown>>;
  before_len?: number;
  after_len?: number;
  before?: unknown;
  after?: unknown;
}

export interface FlattenedContextDiffLine {
  key: string;
  text: string;
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "—";
  }
  if (typeof value === "string") {
    return value;
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

/** Flatten nested context diff nodes into display lines for operator QA panels. */
export function flattenContextDiffLines(
  diff: SupervisorContextDiffNode,
  prefix = "",
): FlattenedContextDiffLine[] {
  const lines: FlattenedContextDiffLine[] = [];

  for (const [key, value] of Object.entries(diff.added ?? {})) {
    lines.push({ key: `${prefix}${key}`, text: `+${formatValue(value)}` });
  }
  for (const [key, value] of Object.entries(diff.removed ?? {})) {
    lines.push({ key: `${prefix}${key}`, text: `-${formatValue(value)}` });
  }
  for (const [key, value] of Object.entries(diff.changed ?? {})) {
    lines.push({
      key: `${prefix}${key}`,
      text: `${formatValue(value.before)} → ${formatValue(value.after)}`,
    });
  }
  for (const [key, nested] of Object.entries(diff.nested ?? {})) {
    lines.push(...flattenContextDiffLines(nested, `${prefix}${key}.`));
  }
  if (Array.isArray(diff.added_items) && diff.added_items.length > 0) {
    lines.push({
      key: `${prefix}[append]`,
      text: `+${diff.added_items.length} item(s): ${formatValue(diff.added_items)}`,
    });
  }
  if (Array.isArray(diff.removed_items) && diff.removed_items.length > 0) {
    lines.push({
      key: `${prefix}[remove]`,
      text: `-${diff.removed_items.length} item(s): ${formatValue(diff.removed_items)}`,
    });
  }
  if (Array.isArray(diff.item_changes) && diff.item_changes.length > 0) {
    lines.push({
      key: `${prefix}[items]`,
      text: `${diff.item_changes.length} item change(s)`,
    });
  }
  if (diff.before !== undefined && diff.after !== undefined && !diff.changed && !diff.nested) {
    lines.push({
      key: prefix || "value",
      text: `${formatValue(diff.before)} → ${formatValue(diff.after)}`,
    });
  }

  return lines;
}
