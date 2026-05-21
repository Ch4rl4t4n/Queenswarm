/** Goal tokenization + graph node matching for Agents context graph focus. */

export interface HiveGraphFocusNode {
  id: string;
  label: string;
}

export interface HiveGraphSemanticHit {
  id?: string | null;
  document?: string | null;
  metadata?: Record<string, unknown>;
}

/** Extract meaningful tokens from a supervisor session goal. */
export function probeGoalTokens(goal: string, limit = 8): string[] {
  const tokens = goal
    .toLowerCase()
    .split(/[^a-z0-9]+/g)
    .map((token) => token.trim())
    .filter((token) => token.length >= 4);
  return [...new Set(tokens)].slice(0, limit);
}

function hitHaystack(hit: HiveGraphSemanticHit): string {
  const meta = hit.metadata ?? {};
  const title = typeof meta.title === "string" ? meta.title : "";
  const source = typeof meta.source_path === "string" ? meta.source_path : "";
  const deliverable = typeof meta.deliverable_id === "string" ? meta.deliverable_id : "";
  const document = typeof hit.document === "string" ? hit.document : "";
  return `${title} ${source} ${deliverable} ${document} ${hit.id ?? ""}`.toLowerCase();
}

/** Match graph nodes against semantic search hits and goal tokens. */
export function matchGraphNodeFocusIds(
  nodes: HiveGraphFocusNode[],
  hits: HiveGraphSemanticHit[],
  goalTokens: string[],
): Set<string> {
  const focused = new Set<string>();

  for (const node of nodes) {
    const nodeHay = `${node.label} ${node.id}`.toLowerCase();
    for (const token of goalTokens) {
      if (nodeHay.includes(token)) {
        focused.add(node.id);
        break;
      }
    }
  }

  for (const hit of hits) {
    const hay = hitHaystack(hit);
    for (const node of nodes) {
      const label = node.label.toLowerCase();
      const id = node.id.toLowerCase();
      if (hay.includes(label) || (label.length >= 4 && hay.includes(label.slice(0, 4)))) {
        focused.add(node.id);
      }
      if (hit.id && (hit.id === node.id || hay.includes(id))) {
        focused.add(node.id);
      }
    }
  }

  return focused;
}

/** Build a compact search query from session goal text. */
export function goalSearchQuery(goal: string, maxLen = 160): string {
  const cleaned = goal.replace(/\s+/g, " ").trim();
  if (cleaned.length <= maxLen) {
    return cleaned;
  }
  return cleaned.slice(0, maxLen);
}
