import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  Building2,
  ClipboardList,
  Coins,
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

export interface SettingsNavSection {
  href: string;
  label: string;
  icon: LucideIcon;
  featureKey?: string;
  /** Visible only when dashboard user is admin on internal tenant. */
  adminOnly?: boolean;
}

export const SETTINGS_NAV_SECTIONS: SettingsNavSection[] = [
  { href: "/settings/security", label: "Security · 2FA", icon: Shield, featureKey: "settings" },
  { href: "/settings/billing", label: "Billing · Usage", icon: Coins, featureKey: "billing_settings" },
  { href: "/settings/team", label: "Team · RBAC", icon: Users, featureKey: "team_rbac" },
  { href: "/settings/sharing", label: "Public sharing", icon: Globe, featureKey: "sharing_settings" },
  { href: "/settings/llm-keys", label: "AI · Voice keys", icon: Mic, featureKey: "llm_keys_settings" },
  { href: "/settings/notifications", label: "Notifications", icon: AlertTriangle, featureKey: "settings" },
  { href: "/settings/capabilities", label: "Capabilities · atlas", icon: Map, featureKey: "settings" },
  { href: "/settings/harness", label: "AI · harness", icon: Brain, featureKey: "ai_harness_dashboard" },
  { href: "/settings/api-keys", label: "API · external keys", icon: KeyRound, featureKey: "api_keys_settings" },
  { href: "/settings/audit", label: "Audit log", icon: ClipboardList, featureKey: "audit_settings" },
  { href: "/settings/enterprise", label: "Enterprise", icon: Building2, featureKey: "enterprise_workspace" },
  {
    href: "/settings/platform",
    label: "Platform · features",
    icon: LayoutGrid,
    featureKey: "platform_features_admin",
    adminOnly: true,
  },
  {
    href: "/settings/accounts",
    label: "Accounts · CMS",
    icon: UserCog,
    featureKey: "accounts_admin",
    adminOnly: true,
  },
  {
    href: "/settings/command-center",
    label: "Command center",
    icon: Activity,
    featureKey: "command_center_admin",
    adminOnly: true,
  },
];

export function filterSettingsNavSections(
  features: Record<string, boolean>,
  options?: { isAdmin?: boolean; platformMode?: string },
): SettingsNavSection[] {
  const base = filterNavByFeatures(SETTINGS_NAV_SECTIONS, features);
  return base.filter((section) => {
    if (!section.adminOnly) {
      return true;
    }
    return Boolean(options?.isAdmin) && options?.platformMode === "internal";
  });
}
