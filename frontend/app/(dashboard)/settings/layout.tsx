import type { ReactNode } from "react";

import { SettingsLayoutClient } from "@/components/hive/settings-layout-client";

interface SettingsLayoutProps {
  children: ReactNode;
}

export default function SettingsLayout({ children }: SettingsLayoutProps) {
  return <SettingsLayoutClient>{children}</SettingsLayoutClient>;
}
