"use client";

import Link from "next/link";
import { ArrowRight, BookOpen, Sparkles } from "lucide-react";

import { V4Card, V4CardHeader } from "@/components/ui/v4";

interface MissionHomeDailyStartCardProps {
  /** Jarvis step count when advisor strip is enabled. */
  jarvisStepCount: number;
  /** Pending simulate-first approvals (non-Gumroad). */
  approvalCount: number;
  manualHref?: string;
  id?: string;
}

/** Plain-language daily ritual guide for Personal OS Mission Home (POS-UX lite). */
export function MissionHomeDailyStartCard({
  jarvisStepCount,
  approvalCount,
  manualHref = "/manual#tasks",
  id,
}: MissionHomeDailyStartCardProps): JSX.Element {
  return (
    <V4Card
      id={id}
      className="scroll-mt-24 md:max-lg:col-span-2 border-cyan/30"
      data-testid="mission-home-daily-start"
    >
      <V4CardHeader
        kicker="Denný štart"
        title="Tri kroky — nič iné teraz nepotrebuješ"
        description="Mission Control = tvoj ranný checklist. Ostatné panely sú voliteľné (Pokročilé dole)."
      />
      <ol className="space-y-2 px-4 pb-4 text-sm text-(--qs-text-2)">
        <li className="flex gap-2">
          <Sparkles className="mt-0.5 size-4 shrink-0 text-pollen" aria-hidden />
          <span>
            <strong className="text-(--qs-text)">1. Jarvis</strong> — max 3 úlohy s tlačidlom „Do this“. Schvaľ len
            veci, ktoré prešli simuláciou.
          </span>
        </li>
        <li className="flex gap-2">
          <span className="mt-0.5 font-mono text-xs font-bold text-cyan">KB</span>
          <span>
            <strong className="text-(--qs-text)">2. Kanban</strong> — tvoje reálne úlohy (Najman, E-shop…). Presúvaj
            stĺpce alebo „Dispatch“ na rozpad.
          </span>
        </li>
        <li className="flex gap-2">
          <span className="mt-0.5 font-mono text-xs font-bold text-[#00FF88]">✓</span>
          <span>
            <strong className="text-(--qs-text)">3. Večer</strong> —{" "}
            <Link href="/ballroom" className="text-cyan underline">
              Ballroom
            </Link>{" "}
            Dump &amp; Sleep.
          </span>
        </li>
      </ol>
      <div className="flex flex-wrap items-center gap-2 border-t border-(--qs-border)/40 px-4 py-3">
        {jarvisStepCount > 0 ? (
          <span className="text-xs text-pollen">{jarvisStepCount} Jarvis krok(ov) čaká</span>
        ) : null}
        {approvalCount > 0 ? (
          <span className="text-xs text-cyan">{approvalCount} schválení v inboxe</span>
        ) : null}
        <Link href={manualHref} className="qs-btn qs-btn--ghost qs-btn--sm ml-auto inline-flex gap-1">
          <BookOpen className="size-3.5" aria-hidden />
          Návod
          <ArrowRight className="size-3.5" aria-hidden />
        </Link>
      </div>
    </V4Card>
  );
}
