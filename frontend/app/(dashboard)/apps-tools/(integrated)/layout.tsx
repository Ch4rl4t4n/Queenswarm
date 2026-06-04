import type { ReactNode } from "react";

import { AppsToolsIntegratedShell } from "@/components/apps-tools/apps-tools-integrated-shell";

interface AppsToolsIntegratedLayoutProps {
  children: ReactNode;
}

/** Factory + module index — always Apps & Tools shell with primary/subnav (no client pathname gate). */
export default function AppsToolsIntegratedLayout({ children }: AppsToolsIntegratedLayoutProps): JSX.Element {
  return <AppsToolsIntegratedShell>{children}</AppsToolsIntegratedShell>;
}
