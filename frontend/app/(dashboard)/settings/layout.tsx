import type { ReactNode } from "react";

import { SettingsSubnav } from "@/components/hive/settings-subnav";

interface SettingsLayoutProps {
  children: ReactNode;
}

export default function SettingsLayout({ children }: SettingsLayoutProps) {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 pb-24 lg:px-10">
      <header className="mb-8">
        <h1 className="font-[family-name:var(--font-poppins)] text-3xl font-bold text-[#fafafa]">Settings</h1>
        <p className="mt-2 font-[family-name:var(--font-poppins)] text-sm text-zinc-500">
          Security · LLM vault · Notifications · External API keys — four operator surfaces.
        </p>
      </header>
      <div className="flex flex-col gap-8 lg:flex-row lg:items-start">
        <SettingsSubnav />
        <div className="min-h-[320px] min-w-0 flex-1">{children}</div>
      </div>
    </div>
  );
}
