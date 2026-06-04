"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

import { AppsToolsSubnav } from "@/components/apps-tools/apps-tools-subnav";
import { SkillFactoryNavProvider } from "@/components/apps-tools/skill-factory-nav-context";
import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HiveSubnavContent } from "@/components/hive/hive-subnav-stack";
import { appsToolsShellActiveForPathname } from "@/lib/apps-tools-routes";

interface AppsToolsLayoutClientProps {
  children: ReactNode;
}

/** Shared Apps & Tools shell for module index and factory modules; other module workspaces pass through. */
export function AppsToolsLayoutClient({ children }: AppsToolsLayoutClientProps): JSX.Element {
  const pathname = usePathname();

  if (!appsToolsShellActiveForPathname(pathname)) {
    return <>{children}</>;
  }

  return (
    <SkillFactoryNavProvider>
      <HivePageShell
        title="Apps & Tools"
        subtitle="Modular workspace index. Each module is isolated by purpose and connected through capability contracts."
        hintKey="appsTools"
        canvasClassName="gap-5"
        subnav={<AppsToolsSubnav />}
      >
        <HiveSubnavContent>{children}</HiveSubnavContent>
      </HivePageShell>
    </SkillFactoryNavProvider>
  );
}
