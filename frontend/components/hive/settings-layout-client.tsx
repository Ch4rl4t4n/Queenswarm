"use client";

import type { ReactNode } from "react";

import { SettingsLanguageSwitch } from "@/components/hive/settings-language-switch";
import { SettingsSubnav } from "@/components/hive/settings-subnav";
import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { V4PageCanvas } from "@/components/ui/v4";
import { localizeDescription } from "@/lib/ui-copy";

interface SettingsLayoutClientProps {
  children: ReactNode;
}

/** Settings shell — Hive Control V4 (matches design-reference SettingsScreen). */
export function SettingsLayoutClient({ children }: SettingsLayoutClientProps) {
  const { language } = useUiLanguage();

  return (
    <V4PageCanvas className="gap-5">
      <header className="qs-page-header mb-3 flex items-start justify-between gap-3">
        <div className="page-title min-w-0 flex-1 space-y-2">
          <h1>Settings</h1>
          <p className="description max-w-2xl font-(family-name:--font-poppins) text-[15px] leading-relaxed text-(--qs-text-3)">
            {localizeDescription(language, {
              en: "Security · Billing · Costs · Team RBAC · Sharing · AI vault · Notifications · API keys · Audit",
              sk: "Bezpečnosť tenantu, billing, náklady, prístup tímu, zdieľanie, AI vault, notifikácie, API kľúče a audit log — názvy sekcií ostávajú v angličtine.",
            })}
          </p>
        </div>
        <SettingsLanguageSwitch compact className="shrink-0" />
      </header>
      <SettingsSubnav />
      <div className="min-w-0">{children}</div>
    </V4PageCanvas>
  );
}
