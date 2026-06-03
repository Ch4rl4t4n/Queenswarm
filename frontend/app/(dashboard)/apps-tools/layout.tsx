import type { ReactNode } from "react";

import { AppsToolsLayoutClient } from "@/components/apps-tools/apps-tools-layout-client";

interface AppsToolsLayoutProps {
  children: ReactNode;
}

export default function AppsToolsLayout({ children }: AppsToolsLayoutProps) {
  return <AppsToolsLayoutClient>{children}</AppsToolsLayoutClient>;
}
