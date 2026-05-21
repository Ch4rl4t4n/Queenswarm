"use client";

import type { ReactNode } from "react";

import { SettingsLanguageSwitch } from "@/components/hive/settings-language-switch";
import { SettingsSubnav } from "@/components/hive/settings-subnav";
import { V4PageCanvas } from "@/components/ui/v4";

interface SettingsLayoutClientProps {
  children: ReactNode;
}

/** Settings shell — Hive Control V4 (matches design-reference SettingsScreen). */
export function SettingsLayoutClient({ children }: SettingsLayoutClientProps) {
  return (
    <V4PageCanvas className="gap-5">
      <header className="qs-page-header mb-3 flex items-center justify-between gap-3">
        <div className="page-title min-w-0 flex-1 space-y-2">
          <h1>Settings</h1>
          <p className="description max-w-2xl font-(family-name:--font-poppins) text-[15px] leading-relaxed text-(--qs-text-3)">
            Security · Billing · Team RBAC · Sharing · AI vault · Notifications · API keys · Audit
          </p>
        </div>
        <SettingsLanguageSwitch compact className="shrink-0" />
      </header>
      <SettingsSubnav />
      <div className="min-w-0">{children}</div>
    </V4PageCanvas>
  );
}
