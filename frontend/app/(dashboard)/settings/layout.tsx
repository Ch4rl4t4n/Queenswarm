import type { ReactNode } from "react";

import { SettingsLanguageSwitch } from "@/components/hive/settings-language-switch";
import { SettingsSubnav } from "@/components/hive/settings-subnav";

interface SettingsLayoutProps {
  children: ReactNode;
}

export default function SettingsLayout({ children }: SettingsLayoutProps) {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 pb-24 lg:px-10">
      <header className="mb-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="font-[family-name:var(--font-poppins)] text-3xl font-bold text-[#fafafa]">Settings</h1>
          <SettingsLanguageSwitch />
        </div>
        <p className="mt-2 font-[family-name:var(--font-poppins)] text-sm text-zinc-500">
          Billing/Usage · Team RBAC · Public sharing · Security · LLM vault · Notifications · External API keys.
        </p>
      </header>
      <div className="flex flex-col gap-8 lg:flex-row lg:items-start">
        <SettingsSubnav />
        <div className="min-h-[320px] min-w-0 flex-1">{children}</div>
      </div>
    </div>
  );
}
