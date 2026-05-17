/** Phase 3 Communication & Knowledge — catalog helpers for `/connectors` cockpit. */

export interface Phase3ToolManifest {
  name: string;
  path: string;
  method: string;
  description?: string;
  headers?: Record<string, string>;
}

export interface Phase3TemplatePublic {
  template_id: string;
  category: string;
  title: string;
  summary: string;
  documentation_url: string;
  suggested_slug: string;
  auth_type: string;
  base_url: string | null;
  suggested_manager_slugs: string[];
  tools: Phase3ToolManifest[];
  tool_count: number;
}

export interface Phase3CatalogSlice {
  template_count: number;
  template_ids: string[];
  templates: Phase3TemplatePublic[];
  grouped: Record<string, Phase3TemplatePublic[]>;
}

export interface ObsidianVaultStatusPayload {
  enabled: boolean;
  poll_interval_sec: number;
  max_files_per_sync: number;
  snapshot: Record<string, unknown>;
}

export const PHASE3_CATEGORY_ORDER = [
  "email",
  "calendar",
  "devtools",
  "chat",
  "knowledge",
  "billing",
  "vault",
] as const;

export function phase3CategoryLabel(category: string): string {
  switch (category) {
    case "email":
      return "Email";
    case "calendar":
      return "Calendar";
    case "devtools":
      return "Git & code hosts";
    case "chat":
      return "Chat & notifications";
    case "knowledge":
      return "Knowledge bases";
    case "billing":
      return "Billing";
    case "vault":
      return "Vault sync";
    default:
      return category;
  }
}

/** Stable ordering: known lanes first, then any unexpected backend categories. */
export function orderedPhase3Categories(grouped: Record<string, Phase3TemplatePublic[]>): string[] {
  const keys = Object.keys(grouped);
  const primary = PHASE3_CATEGORY_ORDER.filter((c) => keys.includes(c));
  const tail = keys.filter((k) => !PHASE3_CATEGORY_ORDER.includes(k as (typeof PHASE3_CATEGORY_ORDER)[number])).sort();
  return [...primary, ...tail];
}

export function extractPhase3FromCatalog(body: unknown): Phase3CatalogSlice | null {
  if (typeof body !== "object" || body === null) {
    return null;
  }
  const phase3 = (body as { phase3?: unknown }).phase3;
  if (typeof phase3 !== "object" || phase3 === null) {
    return null;
  }
  const slice = phase3 as Partial<Phase3CatalogSlice>;
  if (!Array.isArray(slice.templates) || typeof slice.grouped !== "object" || slice.grouped === null) {
    return null;
  }
  return {
    template_count: typeof slice.template_count === "number" ? slice.template_count : slice.templates.length,
    template_ids: Array.isArray(slice.template_ids) ? slice.template_ids.map(String) : [],
    templates: slice.templates as Phase3TemplatePublic[],
    grouped: slice.grouped as Record<string, Phase3TemplatePublic[]>,
  };
}

export interface Phase3CoverageRow {
  template_id: string;
  suggested_slug: string;
  title: string;
  provisioned: boolean;
}

export function phase3ProvisionCoverage(
  templates: Phase3TemplatePublic[],
  connectorSlugs: string[],
): Phase3CoverageRow[] {
  const slugSet = new Set(connectorSlugs.map((s) => s.trim().toLowerCase()));
  return templates.map((tpl) => ({
    template_id: tpl.template_id,
    suggested_slug: tpl.suggested_slug,
    title: tpl.title,
    provisioned: slugSet.has(tpl.suggested_slug.trim().toLowerCase()),
  }));
}

export function buildManifestJsonFromTemplate(tools: Phase3ToolManifest[]): string {
  return JSON.stringify({ tools }, null, 2);
}
