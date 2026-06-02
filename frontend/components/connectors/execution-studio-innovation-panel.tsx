"use client";

import { Lightbulb } from "lucide-react";

import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { InnovationLabPanel } from "@/components/hive/innovation-lab-panel";
import { V4Card, V4CardHeader } from "@/components/ui/v4";

/** Execution Studio — Innovation Lab workspace (approve, implement, Maintainer handoff). */
export function ExecutionStudioInnovationPanel() {
  return (
    <V4Card id="innovation-lab">
      <V4CardHeader
        as="h3"
        kicker="Innovation Lab"
        title="Brainstorm → approve → auto-implement"
        description="Propose features, review risk, pass viability gate, queue Queen Maintainer for PR-only delivery."
        hint={sectionHintNode("innovationViability")}
      />
      <InnovationLabPanel />
    </V4Card>
  );
}

export const EXECUTION_STUDIO_INNOVATION_SECTION = {
  id: "innovation" as const,
  label: "Innovation",
  icon: Lightbulb,
};
