import type { ReactNode } from "react";

import { HivePageHeader } from "@/components/hive/hive-page-header";
import { SettingsSubnav } from "@/components/hive/settings-subnav";

interface SettingsLayoutProps {
  children: ReactNode;
}

export default function SettingsLayout({ children }: SettingsLayoutProps) {
  return (
    <div className="mx-auto w-full max-w-5xl space-y-10">
      <HivePageHeader title="Settings" subtitle="Hive configuration · 7 sections · JWT scopes enforced server-side" />
      <div className="flex flex-col gap-8 lg:flex-row">
        <aside className="lg:sticky lg:top-28 lg:self-start">
          <SettingsSubnav />
        </aside>
        <section className="min-w-0 flex-1">{children}</section>
      </div>
    </div>
  );
}
