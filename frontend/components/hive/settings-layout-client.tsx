"use client";

import type { ReactNode } from "react";

import { HivePageHeader } from "@/components/hive/hive-page-header";
import { SettingsLanguageSwitch } from "@/components/hive/settings-language-switch";
import { SettingsSubnav } from "@/components/hive/settings-subnav";
import { V4PageCanvas } from "@/components/ui/v4";

interface SettingsLayoutClientProps {
  children: ReactNode;
}

/** Settings shell — Hive Control V4 (matches design-reference SettingsScreen). */
export function SettingsLayoutClient({ children }: SettingsLayoutClientProps) {
  return (
    <V4PageCanvas>
      <HivePageHeader
        title="Settings"
        subtitle="Security · Billing · Team RBAC · Sharing · AI vault · Notifications · API keys · Audit"
        actions={<SettingsLanguageSwitch />}
      />
      <SettingsSubnav />
      <div className="min-w-0">{children}</div>
    </V4PageCanvas>
  );
}
