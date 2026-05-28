/** Persisted sub-navigation tab order (per menu key, localStorage). */

export const SUBNAV_ORDER_STORAGE_PREFIX = "queenswarm:subnav-order:";
export const SUBNAV_DISABLED_STORAGE_PREFIX = "queenswarm:subnav-disabled:";
export const SUBNAV_VISIBILITY_EVENT = "queenswarm:subnav-visibility";

/** Menu keys used by primary horizontal sub-nav rows (HiveSubnavRow menuKey). */
export const SUBNAV_MENU_KEYS = {
  integrationsPrimary: "integrations-primary",
  integrationsHub: "integrations-hub",
  knowledgePrimary: "knowledge-primary",
  knowledgeHivemind: "knowledge-hivemind",
  agentsEcosystem: "agents-ecosystem",
  cockpitPrimary: "cockpit-primary",
  settingsHarness: "settings-harness",
  settingsHarnessRules: "settings-harness-rules",
  settingsGroups: "settings-groups",
  settingsSections: "settings-sections",
  executionStudioPanel: "execution-studio-panel",
  executionStudioWorkspace: "execution-studio-workspace",
} as const;

export function subnavOrderStorageKey(menuKey: string): string {
  return `${SUBNAV_ORDER_STORAGE_PREFIX}${menuKey}`;
}

export function subnavDisabledStorageKey(menuKey: string): string {
  return `${SUBNAV_DISABLED_STORAGE_PREFIX}${menuKey}`;
}

export function loadSubnavDisabledIds(menuKey: string): Set<string> {
  if (typeof window === "undefined") {
    return new Set();
  }
  try {
    const raw = window.localStorage.getItem(subnavDisabledStorageKey(menuKey));
    if (!raw) {
      return new Set();
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return new Set();
    }
    return new Set(parsed.filter((id): id is string => typeof id === "string"));
  } catch {
    return new Set();
  }
}

export function saveSubnavDisabledIds(menuKey: string, disabledIds: ReadonlySet<string>): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(subnavDisabledStorageKey(menuKey), JSON.stringify([...disabledIds]));
  } catch {
    /* quota / private mode */
  }
}

export function dispatchSubnavVisibilityChange(menuKey: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new CustomEvent(SUBNAV_VISIBILITY_EVENT, { detail: { menuKey } }));
}

/** Operator-enabled tab ids — at least one always remains enabled. */
export function filterEnabledSubnavIds(menuKey: string, allIds: readonly string[]): string[] {
  if (allIds.length === 0) {
    return [];
  }
  if (typeof window === "undefined") {
    return [...allIds];
  }
  const disabled = loadSubnavDisabledIds(menuKey);
  const enabled = allIds.filter((id) => !disabled.has(id));
  return enabled.length > 0 ? enabled : [...allIds];
}

export function isSubnavSectionEnabled(menuKey: string, sectionId: string, allIds: readonly string[]): boolean {
  return filterEnabledSubnavIds(menuKey, allIds).includes(sectionId);
}

/** Merge saved order with current defaults — keeps unknown ids out, appends new tabs. */
export function mergeSubnavOrder(saved: string[], defaultIds: readonly string[]): string[] {
  const defaults = [...defaultIds];
  const kept = saved.filter((id) => defaults.includes(id));
  const missing = defaults.filter((id) => !kept.includes(id));
  return [...kept, ...missing];
}

export function loadSubnavOrder(menuKey: string, defaultIds: readonly string[]): string[] {
  if (typeof window === "undefined") {
    return [...defaultIds];
  }
  try {
    const raw = window.localStorage.getItem(subnavOrderStorageKey(menuKey));
    if (!raw) {
      return [...defaultIds];
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [...defaultIds];
    }
    return mergeSubnavOrder(parsed.filter((id): id is string => typeof id === "string"), defaultIds);
  } catch {
    return [...defaultIds];
  }
}

export function saveSubnavOrder(menuKey: string, order: string[]): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(subnavOrderStorageKey(menuKey), JSON.stringify(order));
  } catch {
    /* quota / private mode */
  }
}

export function applySubnavOrder<T extends { id: string }>(items: T[], order: readonly string[]): T[] {
  const byId = new Map(items.map((item) => [item.id, item]));
  const ordered: T[] = [];
  for (const id of order) {
    const row = byId.get(id);
    if (row) {
      ordered.push(row);
      byId.delete(id);
    }
  }
  for (const row of byId.values()) {
    ordered.push(row);
  }
  return ordered;
}

/** First tab id in operator's saved order (falls back to first visible default). */
export function primarySubnavDefaultId<T extends string>(
  menuKey: string,
  visibleIds: readonly T[],
  legacyDefaultId: T,
): T {
  if (visibleIds.length === 0) {
    return legacyDefaultId;
  }
  const ordered = loadSubnavOrder(menuKey, visibleIds);
  const first = ordered.find((id) => visibleIds.includes(id as T));
  return (first as T | undefined) ?? visibleIds[0] ?? legacyDefaultId;
}

/** Prefer explicit URL selection; otherwise first enabled tab in saved menu order. */
export function resolvePrimarySubnavFromUrl<T extends string>(params: {
  menuKey: string;
  visibleIds: readonly T[];
  fromUrl: T | null | undefined;
  legacyDefaultId: T;
}): T {
  const enabledIds = filterEnabledSubnavIds(params.menuKey, params.visibleIds) as T[];
  const enabledSet = new Set(enabledIds);
  if (params.fromUrl && enabledSet.has(params.fromUrl)) {
    return params.fromUrl;
  }
  return primarySubnavDefaultId(params.menuKey, enabledIds, params.legacyDefaultId);
}
