"use client";

import type { ReactNode } from "react";

import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HiveSubnavContent } from "@/components/hive/hive-subnav-stack";
import { SettingsSubnav } from "@/components/hive/settings-subnav";

interface SettingsLayoutClientProps {
  children: ReactNode;
}

/** Settings shell — unified HivePageShell + progressive-disclosure sub-nav + panel content. */
export function SettingsLayoutClient({ children }: SettingsLayoutClientProps) {
  return (
    <HivePageShell
      title="Settings"
      subtitle="Tenant security, AI keys, notifications, team access, and audit — configure how your hive behaves."
      hintKey="settings"
      canvasClassName="gap-5"
      subnav={<SettingsSubnav />}
    >
      <HiveSubnavContent>{children}</HiveSubnavContent>
    </HivePageShell>
  );
}
