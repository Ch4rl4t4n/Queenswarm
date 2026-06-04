"use client";

import type { ReactNode } from "react";

import { AppsToolsSubnav } from "@/components/apps-tools/apps-tools-subnav";
import { SkillFactoryNavProvider } from "@/components/apps-tools/skill-factory-nav-context";
import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HiveSubnavContent } from "@/components/hive/hive-subnav-stack";

interface AppsToolsIntegratedShellProps {
  children: ReactNode;
}

/** Shared Apps & Tools shell for module index, Skill Factory, and Pack Factory. */
export function AppsToolsIntegratedShell({ children }: AppsToolsIntegratedShellProps): JSX.Element {
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
