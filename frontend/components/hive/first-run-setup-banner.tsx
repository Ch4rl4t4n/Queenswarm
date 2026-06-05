"use client";

import Link from "next/link";
import { ArrowRight, Rocket, XIcon } from "lucide-react";
import { memo, useEffect, useState } from "react";

import { usePlatform } from "@/components/hive/platform-context";
import { V4Badge } from "@/components/ui/v4";
import {
  dismissFirstRunWizard,
  isFirstRunWizardDismissed,
} from "@/lib/first-run-wizard";
import { useSoloFirstRun } from "@/lib/use-solo-first-run";

/** Compact first-run nudge on Agentic OS Overview until setup is complete (OW5). */
function FirstRunSetupBannerInner(): JSX.Element | null {
  const { soloMode } = usePlatform();
  const [dismissed, setDismissed] = useState(true);
  const { data, loading } = useSoloFirstRun({ enabled: soloMode });

  useEffect(() => {
    setDismissed(isFirstRunWizardDismissed());
  }, []);

  if (!soloMode || dismissed || loading || !data?.enabled || data.complete) {
    return null;
  }

  const nextStep = data.steps.find((step) => !step.done);
  if (!nextStep) {
    return null;
  }

  return (
    <div
      className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-pollen/35 bg-pollen/5 px-3 py-2.5"
      role="status"
      aria-label="First-run setup in progress"
    >
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold text-pollen">First-run setup · {data.progress_pct}%</p>
        <p className="mt-0.5 text-[11px] text-(--qs-text-2)">
          Next: <span className="font-medium text-(--qs-text)">{nextStep.label}</span>
          {" — "}
          {nextStep.detail}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <V4Badge tone="warn">Incomplete</V4Badge>
        <Link href="/agents#first-run-wizard" className="qs-btn qs-btn--primary qs-btn--sm gap-1">
          Continue setup
          <ArrowRight className="size-3.5" aria-hidden />
        </Link>
        <Link href={nextStep.href} className="qs-btn qs-btn--ghost qs-btn--sm">
          {nextStep.link_label}
        </Link>
        {nextStep.id === "project_brief" ? (
          <Link
            href="/agents#first-run-wizard"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
            title="Apply starter brief on Agents"
          >
            <Rocket className="size-3.5" aria-hidden />
            Starter brief
          </Link>
        ) : null}
        <button
          type="button"
          className="rounded-md p-1 text-(--qs-text-3) hover:text-(--qs-text)"
          aria-label="Dismiss first-run setup banner"
          onClick={() => {
            dismissFirstRunWizard();
            setDismissed(true);
          }}
        >
          <XIcon className="size-4" aria-hidden />
        </button>
      </div>
    </div>
  );
}

export const FirstRunSetupBanner = memo(FirstRunSetupBannerInner);
