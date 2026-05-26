import { LEADERBOARD_ENABLED, PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";
import { hiveOverviewHref, hiveOverviewLabel } from "@/lib/hive-home-route";

export interface HiveSidebarShortcut {
  href: string;
  label: { en: string; sk: string };
  /** Single letter after Ctrl (lowercase). */
  key: string;
}

/**
 * Ctrl + first meaningful letter per sidebar section.
 * Settings uses ``g`` (settin**G**s) — ``s`` is Swarms.
 */
export function buildHiveSidebarShortcuts(consolidatedEnabled: boolean = PHASE70_CONSOLIDATED_NAV_ENABLED): HiveSidebarShortcut[] {
  const knowledgeHref = consolidatedEnabled ? "/knowledge" : "/hive-mind";
  const integrationsHref = consolidatedEnabled ? "/integrations" : "/connectors";

  const rows: HiveSidebarShortcut[] = [
    { href: hiveOverviewHref(), label: { en: hiveOverviewLabel(), sk: hiveOverviewLabel() }, key: "d" },
    { href: "/swarms", label: { en: "Swarms", sk: "Swarms" }, key: "s" },
    { href: "/agents", label: { en: "Agents", sk: "Agenti" }, key: "a" },
    { href: "/foragers", label: { en: "Foragers", sk: "Foragers" }, key: "f" },
    { href: "/tasks", label: { en: "Tasks", sk: "Tasky" }, key: "t" },
    { href: knowledgeHref, label: { en: "Knowledge", sk: "Knowledge" }, key: "k" },
    { href: integrationsHref, label: { en: "Integrations", sk: "Integrácie" }, key: "i" },
    { href: "/ballroom", label: { en: "Ballroom", sk: "Ballroom" }, key: "b" },
    ...(LEADERBOARD_ENABLED
      ? [{ href: "/leaderboard", label: { en: "Leaderboard", sk: "Leaderboard" }, key: "l" } satisfies HiveSidebarShortcut]
      : []),
    { href: "/settings/security", label: { en: "Settings", sk: "Nastavenia" }, key: "g" },
    { href: "/manual", label: { en: "Manual", sk: "Manuál" }, key: "m" },
  ];

  return rows;
}

export const HIVE_SIDEBAR_SHORTCUTS: HiveSidebarShortcut[] = buildHiveSidebarShortcuts();

/** Resolve href for Ctrl+key (returns null if unmapped). */
export function hiveShortcutHrefForKey(key: string, consolidatedEnabled: boolean = PHASE70_CONSOLIDATED_NAV_ENABLED): string | null {
  const row = buildHiveSidebarShortcuts(consolidatedEnabled).find((s) => s.key === key.toLowerCase());
  return row?.href ?? null;
}
