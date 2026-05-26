import type { ComponentType } from "react";

/** Slug segment after `/settings/` — must match SETTINGS_NAV_SECTIONS hrefs. */
export type SettingsPanelSlug =
  | "security"
  | "billing"
  | "team"
  | "sharing"
  | "llm-keys"
  | "notifications"
  | "capabilities"
  | "harness"
  | "api-keys"
  | "audit"
  | "enterprise"
  | "platform"
  | "accounts"
  | "command-center";

export const DEFAULT_SETTINGS_PANEL: SettingsPanelSlug = "security";

export const SETTINGS_PANEL_SLUGS: readonly SettingsPanelSlug[] = [
  "security",
  "billing",
  "team",
  "sharing",
  "llm-keys",
  "notifications",
  "capabilities",
  "harness",
  "api-keys",
  "audit",
  "enterprise",
  "platform",
  "accounts",
  "command-center",
] as const;

type PanelLoader = () => Promise<{ default: ComponentType<object> }>;

/** Lazy loaders — warmed on idle from SettingsPanelHost. */
export const SETTINGS_PANEL_LOADERS: Record<SettingsPanelSlug, PanelLoader> = {
  security: () =>
    import("@/components/hive/security-2fa-settings").then((mod) => ({
      default: mod.Security2FASettings as ComponentType<object>,
    })),
  billing: () =>
    import("@/components/hive/billing-settings-panel").then((mod) => ({
      default: mod.BillingSettingsPanel as ComponentType<object>,
    })),
  team: () =>
    import("@/components/hive/team-settings-panel").then((mod) => ({
      default: mod.TeamSettingsPanel as ComponentType<object>,
    })),
  sharing: () =>
    import("@/components/hive/sharing-settings-panel").then((mod) => ({
      default: mod.SharingSettingsPanel as ComponentType<object>,
    })),
  "llm-keys": () =>
    import("@/components/hive/settings-llm-keys-panel").then((mod) => ({
      default: mod.SettingsLlmKeysPanel as ComponentType<object>,
    })),
  notifications: () =>
    import("@/components/hive/settings-notifications-panel").then((mod) => ({
      default: mod.SettingsNotificationsPanel as ComponentType<object>,
    })),
  capabilities: () =>
    import("@/components/hive/settings-capabilities-panel").then((mod) => ({
      default: mod.SettingsCapabilitiesPanel as ComponentType<object>,
    })),
  harness: () =>
    import("@/components/hive/settings-harness-settings-view").then((mod) => ({
      default: mod.SettingsHarnessSettingsView as ComponentType<object>,
    })),
  "api-keys": () =>
    import("@/components/hive/settings-api-keys-panel").then((mod) => ({
      default: mod.SettingsApiKeysPanel as ComponentType<object>,
    })),
  audit: () =>
    import("@/components/hive/settings-audit-panel").then((mod) => ({
      default: mod.SettingsAuditPanel as ComponentType<object>,
    })),
  enterprise: () =>
    import("@/components/hive/enterprise-settings-panel").then((mod) => ({
      default: mod.EnterpriseSettingsPanel as ComponentType<object>,
    })),
  platform: () =>
    import("@/components/hive/platform-features-settings-panel").then((mod) => ({
      default: mod.PlatformFeaturesSettingsPanel as ComponentType<object>,
    })),
  accounts: () =>
    import("@/components/hive/admin-accounts-settings-panel").then((mod) => ({
      default: mod.AdminAccountsSettingsPanel as ComponentType<object>,
    })),
  "command-center": () =>
    import("@/components/hive/command-center-settings-panel").then((mod) => ({
      default: mod.CommandCenterSettingsPanel as ComponentType<object>,
    })),
};

export function parseSettingsPanelSlug(pathname: string): SettingsPanelSlug | null {
  const prefix = "/settings/";
  if (!pathname.startsWith(prefix)) {
    return null;
  }
  const slug = pathname.slice(prefix.length).split("/")[0]?.trim();
  if (!slug) {
    return null;
  }
  return (SETTINGS_PANEL_SLUGS as readonly string[]).includes(slug) ? (slug as SettingsPanelSlug) : null;
}

/** True when settings subnav item matches current pathname (catch-all + dedicated routes like costs). */
export function isSettingsNavSectionActive(pathname: string, href: string): boolean {
  const slug = parseSettingsPanelSlug(href);
  const activeSlug = parseSettingsPanelSlug(pathname);
  if (slug !== null && activeSlug !== null) {
    return slug === activeSlug;
  }
  const normalized = pathname.split("#")[0] ?? pathname;
  const base = href.split("#")[0] ?? href;
  return normalized === base || normalized.startsWith(`${base}/`);
}

export function warmAllSettingsPanelChunks(): void {
  for (const loader of Object.values(SETTINGS_PANEL_LOADERS)) {
    void loader();
  }
}
