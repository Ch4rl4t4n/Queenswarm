import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  Building2,
  CircleDollarSign,
  ClipboardList,
  Globe,
  KeyRound,
  LayoutGrid,
  Map,
  Mic,
  Brain,
  Shield,
  Users,
  UserCog,
  Activity,
} from "lucide-react";

import { filterNavByFeatures } from "@/lib/platform-features";
import type { V4SectionTone } from "@/lib/v4-section-tones";

export interface SettingsNavSection {
  href: string;
  label: string;
  icon: LucideIcon;
  featureKey?: string;
  /** Visible only when dashboard user is admin on internal tenant. */
  adminOnly?: boolean;
  /** Accordion nav — short subtitle under the title. */
  hint?: string;
  /** Accordion nav — right meta (e.g. "2FA · vault"). */
  shortLabel?: string;
  /** Accordion nav — neon section tone. */
  tone?: V4SectionTone;
}

export type SettingsNavGroupId = "essential" | "operator" | "admin";

export interface SettingsNavGroup {
  id: SettingsNavGroupId;
  label: string;
  sectionHrefs: string[];
  /** Visible only when dashboard user is admin on internal tenant. */
  adminOnly?: boolean;
}

/** Three-tier settings IA — Essentials (default) · Advanced · Admin. */
export const SETTINGS_NAV_GROUPS: SettingsNavGroup[] = [
  {
    id: "essential",
    label: "Essentials",
    sectionHrefs: ["/settings/security", "/settings/notifications", "/settings/llm-keys"],
  },
  {
    id: "operator",
    label: "Advanced",
    sectionHrefs: [
      "/settings/harness",
      "/settings/capabilities",
      "/settings/costs",
      "/settings/api-keys",
      "/settings/audit",
      "/settings/team",
      "/settings/sharing",
      "/settings/enterprise",
    ],
  },
  {
    id: "admin",
    label: "Admin",
    sectionHrefs: ["/settings/platform", "/settings/accounts", "/settings/command-center"],
    adminOnly: true,
  },
];

export const SETTINGS_NAV_SECTIONS: SettingsNavSection[] = [
  {
    href: "/settings/security",
    label: "Security",
    icon: Shield,
    featureKey: "settings",
    tone: "purple",
    hint: "Passwords · authenticator · backup codes",
    shortLabel: "Vault",
  },
  { href: "/settings/costs", label: "Costs", icon: CircleDollarSign, featureKey: "costs", tone: "cyan", hint: "LLM spend · swarm budgets", shortLabel: "Spend" },
  {
    href: "/settings/team",
    label: "Team",
    icon: Users,
    featureKey: "team_rbac",
    tone: "amber",
    hint: "Members · roles · invites",
    shortLabel: "RBAC",
  },
  {
    href: "/settings/sharing",
    label: "Public sharing",
    icon: Globe,
    featureKey: "sharing_settings",
    tone: "green",
    hint: "Public links · embed · revoke",
    shortLabel: "Share",
  },
  {
    href: "/settings/llm-keys",
    label: "LLM & voice",
    icon: Mic,
    featureKey: "llm_keys_settings",
    tone: "cyan",
    hint: "Provider keys · voice lanes",
    shortLabel: "Keys",
  },
  {
    href: "/settings/notifications",
    label: "Notifications",
    icon: AlertTriangle,
    featureKey: "settings",
    tone: "magenta",
    hint: "Email · SMS · Discord · Teams",
    shortLabel: "Channels",
  },
  {
    href: "/settings/capabilities",
    label: "Capabilities",
    icon: Map,
    featureKey: "settings",
    tone: "green",
    hint: "Live map · planned rollout",
    shortLabel: "Atlas",
  },
  {
    href: "/settings/harness",
    label: "AI harness",
    icon: Brain,
    featureKey: "ai_harness_dashboard",
    tone: "purple",
    hint: "Behavioral memory · Queen prompts",
    shortLabel: "Harness",
  },
  {
    href: "/settings/api-keys",
    label: "API keys",
    icon: KeyRound,
    featureKey: "api_keys_settings",
    tone: "pollen",
    hint: "Webhook secrets · external bundles",
    shortLabel: "API",
  },
  {
    href: "/settings/audit",
    label: "Audit log",
    icon: ClipboardList,
    featureKey: "audit_settings",
    tone: "red",
    hint: "Admin actions · overrides · exports",
    shortLabel: "Audit",
  },
  {
    href: "/settings/enterprise",
    label: "Enterprise",
    icon: Building2,
    featureKey: "enterprise_workspace",
    tone: "purple",
    hint: "SSO · SCIM · workspace policy",
    shortLabel: "Enterprise",
  },
  {
    href: "/settings/platform",
    label: "Platform features",
    icon: LayoutGrid,
    featureKey: "platform_features_admin",
    adminOnly: true,
    tone: "cyan",
    hint: "Feature matrix · profile toggles",
    shortLabel: "Matrix",
  },
  {
    href: "/settings/accounts",
    label: "Accounts",
    icon: UserCog,
    featureKey: "accounts_admin",
    adminOnly: true,
    tone: "amber",
    hint: "Tenant accounts · CMS lanes",
    shortLabel: "CMS",
  },
  {
    href: "/settings/command-center",
    label: "Command center",
    icon: Activity,
    featureKey: "command_center_admin",
    adminOnly: true,
    tone: "red",
    hint: "Operator overrides · fleet health",
    shortLabel: "Ops",
  },
];

export function filterSettingsNavSections(
  features: Record<string, boolean>,
  options?: { isAdmin?: boolean; platformMode?: string; soloMode?: boolean },
): SettingsNavSection[] {
  const base = filterNavByFeatures(SETTINGS_NAV_SECTIONS, features);
  /** Solo hides multi-tenant B2B lanes only — admin ops (platform, command center) stay visible. */
  const soloHidden = new Set<string>([
    "/settings/team",
    "/settings/sharing",
    "/settings/enterprise",
    "/settings/accounts",
  ]);
  return base.filter((section) => {
    if (options?.soloMode && soloHidden.has(section.href)) {
      return false;
    }
    if (!section.adminOnly) {
      return true;
    }
    return Boolean(options?.isAdmin) && options?.platformMode === "internal";
  });
}

/** Primary settings groups with feature/admin filtering applied. */
export function filterSettingsNavGroups(
  features: Record<string, boolean>,
  options?: { isAdmin?: boolean; platformMode?: string; soloMode?: boolean },
): SettingsNavGroup[] {
  const sections = filterSettingsNavSections(features, options);
  const hrefSet = new Set(sections.map((s) => s.href));
  return SETTINGS_NAV_GROUPS.filter((group) => {
    if (group.adminOnly && !(Boolean(options?.isAdmin) && options?.platformMode === "internal")) {
      return false;
    }
    return group.sectionHrefs.some((href) => hrefSet.has(href));
  }).map((group) => ({
    ...group,
    sectionHrefs: group.sectionHrefs.filter((href) => hrefSet.has(href)),
  }));
}

/** Resolve which primary group owns a settings href. */
export function settingsNavGroupForHref(
  href: string,
  groups: SettingsNavGroup[],
): SettingsNavGroupId | null {
  const match = groups.find((group) => group.sectionHrefs.includes(href));
  return match?.id ?? null;
}
