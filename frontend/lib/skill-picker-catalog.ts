/** Skill picker — pinned favorites, usage tracking, compact vs full catalog. */

export interface SkillCatalogItem {
  slug: string;
  title: string;
  keywords: string[];
  roles: string[];
  is_builtin: boolean;
  is_tenant: boolean;
  usage_count?: number;
}

export const SKILL_PICKER_USAGE_STORAGE_KEY = "queenswarm:skill-picker-usage";
export const SKILL_PICKER_USAGE_SYNCED_KEY = "queenswarm:skill-picker-usage-synced";

/** Operator-facing defaults — builtins used most often in sessions / kanban. */
export const SKILL_PICKER_PINNED_SLUGS: readonly string[] = [
  "context",
  "decide",
  "product-mission",
  "multi-step-reasoning",
  "lead-gen-lane",
  "marketing-campaign-playbook",
  "competitor-scrape-analyze",
  "self-review-loop",
  "automation-proposal",
  "full-swarm-autonomy",
];

export const SKILL_PICKER_COMPACT_LIMIT = 8;

export type SkillUsageMap = Record<string, number>;

export function readSkillUsageMap(): SkillUsageMap {
  if (typeof window === "undefined") {
    return {};
  }
  try {
    const raw = window.localStorage.getItem(SKILL_PICKER_USAGE_STORAGE_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") {
      return {};
    }
    const out: SkillUsageMap = {};
    for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
      if (typeof value === "number" && value > 0) {
        out[key.toLowerCase()] = value;
      }
    }
    return out;
  } catch {
    return {};
  }
}

export function buildSkillUsageMapFromCatalog(catalog: SkillCatalogItem[]): SkillUsageMap {
  const out: SkillUsageMap = {};
  for (const row of catalog) {
    const count = row.usage_count ?? 0;
    if (count > 0) {
      out[row.slug.toLowerCase()] = count;
    }
  }
  return out;
}

/** Backend counts win; localStorage fills gaps until sync completes. */
export function mergeSkillUsageMaps(primary: SkillUsageMap, fallback: SkillUsageMap): SkillUsageMap {
  const out: SkillUsageMap = { ...fallback };
  for (const [slug, count] of Object.entries(primary)) {
    if (count > 0) {
      out[slug] = Math.max(out[slug] ?? 0, count);
    }
  }
  return out;
}

export function clearLocalSkillUsageMap(): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.removeItem(SKILL_PICKER_USAGE_STORAGE_KEY);
    window.localStorage.setItem(SKILL_PICKER_USAGE_SYNCED_KEY, "1");
  } catch {
    /* quota / private mode */
  }
}

export function hasLocalSkillUsagePendingSync(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  try {
    if (window.localStorage.getItem(SKILL_PICKER_USAGE_SYNCED_KEY) === "1") {
      return false;
    }
    return Object.keys(readSkillUsageMap()).length > 0;
  } catch {
    return false;
  }
}

/** Legacy local-only fallback when API is unavailable. */
export function recordSkillUsageLocal(slugs: string[]): void {
  if (typeof window === "undefined" || slugs.length === 0) {
    return;
  }
  const usage = readSkillUsageMap();
  for (const slug of slugs) {
    const key = slug.trim().toLowerCase();
    if (!key) continue;
    usage[key] = (usage[key] ?? 0) + 1;
  }
  try {
    window.localStorage.setItem(SKILL_PICKER_USAGE_STORAGE_KEY, JSON.stringify(usage));
  } catch {
    /* quota / private mode */
  }
}

function usageRank(slug: string, usage: SkillUsageMap): number {
  return usage[slug.toLowerCase()] ?? 0;
}

/** Compact row: suggested → pinned → recent usage → selected; tenant factory only if picked/suggested. */
export function pickCompactSkillSlugs(options: {
  catalog: SkillCatalogItem[];
  selected: string[];
  suggested: string[];
  usage?: SkillUsageMap;
  limit?: number;
}): string[] {
  const { catalog, selected, suggested, usage = {}, limit = SKILL_PICKER_COMPACT_LIMIT } = options;
  const catalogSlugs = new Set(catalog.map((row) => row.slug.toLowerCase()));
  const tenantBySlug = new Map(catalog.map((row) => [row.slug.toLowerCase(), row.is_tenant] as const));
  const seen = new Set<string>();
  const out: string[] = [];

  const push = (slug: string, opts?: { allowTenantDefault?: boolean }): void => {
    const key = slug.trim().toLowerCase();
    if (!key || seen.has(key) || !catalogSlugs.has(key)) {
      return;
    }
    const isTenant = tenantBySlug.get(key) === true;
    if (isTenant && !opts?.allowTenantDefault) {
      const pinned =
        selected.map((s) => s.toLowerCase()).includes(key) || suggested.map((s) => s.toLowerCase()).includes(key);
      if (!pinned) {
        return;
      }
    }
    seen.add(key);
    out.push(key);
  };

  for (const slug of suggested) {
    push(slug, { allowTenantDefault: true });
  }
  for (const slug of selected) {
    push(slug, { allowTenantDefault: true });
  }
  for (const slug of SKILL_PICKER_PINNED_SLUGS) {
    push(slug);
  }

  const usageSorted = Object.entries(usage)
    .filter(([slug]) => catalogSlugs.has(slug))
    .sort((a, b) => b[1] - a[1])
    .map(([slug]) => slug);
  for (const slug of usageSorted) {
    push(slug, { allowTenantDefault: true });
  }

  for (const row of catalog) {
    if (row.is_builtin) {
      push(row.slug);
    }
  }

  return out.slice(0, limit);
}

export function sortCatalogForPicker(catalog: SkillCatalogItem[], usage: SkillUsageMap): SkillCatalogItem[] {
  return [...catalog].sort((a, b) => {
    const usageDiff = usageRank(b.slug, usage) - usageRank(a.slug, usage);
    if (usageDiff !== 0) {
      return usageDiff;
    }
    if (a.is_builtin !== b.is_builtin) {
      return a.is_builtin ? -1 : 1;
    }
    return a.title.localeCompare(b.title);
  });
}
