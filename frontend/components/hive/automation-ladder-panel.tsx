"use client";

import type { JSX } from "react";

import Link from "next/link";
import { Layers } from "lucide-react";

import { AUTOMATION_HYBRID_RULE, AUTOMATION_LADDER_LEVELS } from "@/lib/automation-ladder";
import { MANUAL_HREFS } from "@/lib/manual-routes";
import { V4Badge } from "@/components/ui/v4";

/** Operator guide — which automation level to pick (Brad 5-level framework). */
export function AutomationLadderPanel(): JSX.Element {
  return (
    <section
      className="rounded-xl border border-amber-500/25 bg-amber-500/5 p-4"
      data-testid="automation-ladder-panel"
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Layers className="h-4 w-4 text-pollen" aria-hidden />
        <h3 className="text-sm font-semibold text-(--qs-text)">Automation Ladder</h3>
        <V4Badge tone="gold">L1–L5</V4Badge>
        <Link href={MANUAL_HREFS.manualAutomationLadder} className="ml-auto text-[10px] text-cyan-300 hover:underline">
          Full manual →
        </Link>
      </div>
      <p className="mb-3 text-xs leading-relaxed text-(--qs-text-3)">{AUTOMATION_HYBRID_RULE}</p>
      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
        {AUTOMATION_LADDER_LEVELS.map((row) => (
          <article
            key={row.id}
            className="rounded-lg border border-(--qs-border) bg-black/20 p-3"
          >
            <div className="mb-1 flex items-center gap-2">
              <V4Badge tone="info">L{row.level}</V4Badge>
              <p className="text-xs font-semibold text-(--qs-text)">{row.title}</p>
            </div>
            <p className="text-[11px] leading-relaxed text-(--qs-text-3)">{row.summary}</p>
            <p className="mt-2 font-(family-name:--font-jetbrains-mono) text-[10px] text-cyan-200/90">
              {row.queenswarmPath}
            </p>
            <Link href={row.href} className="mt-2 inline-block text-[10px] text-pollen hover:underline">
              Open →
            </Link>
          </article>
        ))}
      </div>
    </section>
  );
}
