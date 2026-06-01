"use client";

import Link from "next/link";
import { Sparkles, XIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import type { PatternExplorerPayload } from "@/lib/hive-types";
import {
  dismissPatternOnboarding,
  isPatternOnboardingDismissed,
  patternProgressPct,
} from "@/lib/pattern-onboarding";
import { cn } from "@/lib/utils";

interface PatternOnboardingBannerProps {
  data: PatternExplorerPayload;
}

/** First-run + milestone banner — „Your swarm used 5 patterns today“. */
export function PatternOnboardingBanner({ data }: PatternOnboardingBannerProps): JSX.Element | null {
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    setDismissed(isPatternOnboardingDismissed());
  }, []);

  const onboarding = data.onboarding;
  if (!onboarding) {
    return null;
  }

  const progressPct = patternProgressPct(data.unique_patterns_today, onboarding.target_unique_patterns);

  if (dismissed && !onboarding.milestone_reached) {
    return null;
  }

  function handleDismiss(): void {
    dismissPatternOnboarding();
    setDismissed(true);
  }

  return (
    <V4Card className={cn("border-pollen/35", onboarding.milestone_reached && "shadow-[0_0_24px_rgba(255,184,0,0.25)]")}>
      <V4CardHeader
        kicker="Pattern onboarding"
        title={onboarding.headline}
        description="Pattern Router picks primary + secondary agentic patterns at every supervisor session — harness beats raw model."
        actions={
          <button
            type="button"
            className="rounded-md p-1 text-(--qs-text-3) hover:text-(--qs-text)"
            aria-label="Dismiss pattern onboarding"
            onClick={handleDismiss}
          >
            <XIcon className="h-4 w-4" aria-hidden />
          </button>
        }
      />

      <div className="mt-3 space-y-3">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <Sparkles className="h-4 w-4 text-pollen" aria-hidden />
          <span className="font-mono text-cyan">
            {onboarding.progress_unique_patterns}/{onboarding.target_unique_patterns} patterns today
          </span>
          {onboarding.milestone_reached ? <V4Badge tone="ok">Milestone</V4Badge> : <V4Badge tone="info">In progress</V4Badge>}
        </div>

        <div
          className="h-2 overflow-hidden rounded-full bg-black/40"
          role="progressbar"
          aria-valuenow={progressPct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Unique agentic patterns used today"
        >
          <div
            className="h-full rounded-full bg-linear-to-r from-pollen to-cyan transition-[width] duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>

        {!onboarding.has_patterned_sessions ? (
          <div className="flex flex-wrap gap-2">
            {onboarding.starter_patterns.map((row) => (
              <V4Badge key={row.id} tone="info">
                #{row.number} {row.label}
              </V4Badge>
            ))}
          </div>
        ) : null}

        <div className="flex flex-wrap gap-2">
          <Link href="/agents#sessions" className="qs-btn qs-btn--ghost qs-btn--sm">
            {onboarding.has_patterned_sessions ? "Open session composer" : "Open Agents — new session"}
          </Link>
          <Link href="/settings/harness" className="qs-btn qs-btn--ghost qs-btn--sm">
            Pattern catalog
          </Link>
          {onboarding.milestone_reached ? (
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={handleDismiss}>
              Got it
            </button>
          ) : null}
        </div>
      </div>
    </V4Card>
  );
}
