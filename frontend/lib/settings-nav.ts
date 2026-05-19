import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  ClipboardList,
  Coins,
  Globe,
  KeyRound,
  Mic,
  Shield,
  Users,
} from "lucide-react";

export interface SettingsNavSection {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const SETTINGS_NAV_SECTIONS: SettingsNavSection[] = [
  { href: "/settings/security", label: "Security · 2FA", icon: Shield },
  { href: "/settings/billing", label: "Billing · Usage", icon: Coins },
  { href: "/settings/team", label: "Team · RBAC", icon: Users },
  { href: "/settings/sharing", label: "Public sharing", icon: Globe },
  { href: "/settings/llm-keys", label: "AI · Voice keys", icon: Mic },
  { href: "/settings/notifications", label: "Notifications", icon: AlertTriangle },
  { href: "/settings/api-keys", label: "API · external keys", icon: KeyRound },
  { href: "/settings/audit", label: "Audit log", icon: ClipboardList },
];
