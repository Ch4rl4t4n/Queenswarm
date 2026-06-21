"use client";

import Link from "next/link";
import { Brain, CheckCircle2, Circle, Loader2, Sparkles, XIcon } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { usePlatform } from "@/components/hive/platform-context";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError } from "@/lib/api";
import {
  dismissSecondBrainWizard,
  isSecondBrainWizardDismissed,
} from "@/lib/second-brain-wizard";
import { useSecondBrainWizard } from "@/lib/use-second-brain-wizard";

function SecondBrainPackWizardPanelInner(): JSX.Element | null {
  const { soloMode } = usePlatform();
  const [dismissed, setDismissed] = useState(true);
  const { data, loading, seedBusy, reload, seedBrainPack } = useSecondBrainWizard(soloMode);

  useEffect(() => {
    setDismissed(isSecondBrainWizardDismissed());
  }, []);

  const handleSeed = useCallback(async () => {
    try {
      const seeded = await seedBrainPack();
      if (seeded) {
        toast.success("Brain Pack starter seeded — customize SOUL, MEMORY, USER.");
      } else {
        toast.message("Brain Pack already has content — edit in Knowledge.");
      }
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Seed failed.");
    }
  }, [seedBrainPack]);

  const handleDismiss = useCallback(() => {
    dismissSecondBrainWizard();
    setDismissed(true);
  }, []);

  if (!soloMode || dismissed) {
    return null;
  }

  if (loading && !data) {
    return (
      <V4Card className="border-cyan/25">
        <p className="flex items-center gap-2 p-4 text-sm text-(--qs-muted)">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading Second Brain setup…
        </p>
      </V4Card>
    );
  }

  if (!data?.enabled || data.complete) {
    return null;
  }

  const nextStep = data.steps.find((step) => !step.done);

  return (
    <V4Card id="second-brain-wizard" className="border-cyan/30 bg-cyan/5">
      <V4CardHeader
        kicker="Hermes-style · verify-first"
        title="Second Brain Pack"
        description="Three steps — memory, specialist bees, Obsidian or first cycle. System runs; you approve outcomes."
        hint={sectionHintNode("knowledgeBrainPackWizard")}
        actions={
          <div className="flex gap-2">
            <HiveRefreshButton busy={loading} onClick={() => void reload()} />
            <button
              type="button"
              className="rounded-md p-1 text-(--qs-text-3) hover:text-(--qs-text)"
              aria-label="Dismiss Second Brain wizard"
              onClick={handleDismiss}
            >
              <XIcon className="size-4" aria-hidden />
            </button>
          </div>
        }
      />

      <div className="mx-4 mb-3 flex flex-wrap items-center gap-2">
        <V4Badge tone="info">
          <Brain className="mr-1 inline size-3" aria-hidden />
          {data.brain_pack_filled}/{data.brain_pack_total} memory
        </V4Badge>
        <V4Badge tone="purple">
          {data.trio_bound}/{data.trio_total} bees
        </V4Badge>
      </div>

      <div
        className="mx-4 mb-3 h-2 overflow-hidden rounded-full bg-black/40"
        role="progressbar"
        aria-valuenow={data.progress_pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full bg-linear-to-r from-cyan to-pollen transition-[width] duration-500"
          style={{ width: `${data.progress_pct}%` }}
        />
      </div>

      <ol className="space-y-3 px-4 pb-4">
        {data.steps.map((step, idx) => (
          <li key={step.id} className="flex gap-3 text-sm">
            {step.done ? (
              <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-success" aria-hidden />
            ) : (
              <Circle className="mt-0.5 size-5 shrink-0 text-(--qs-text-4)" aria-hidden />
            )}
            <div className="min-w-0 flex-1">
              <p className="font-medium text-(--qs-text)">
                {idx + 1}. {step.label}
                {step.progress_note ? (
                  <span className="ml-2 text-xs font-normal text-(--qs-text-4)">({step.progress_note})</span>
                ) : null}
              </p>
              <p className="mt-0.5 text-xs text-(--qs-text-3)">{step.detail}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <Link href={step.href} className="qs-btn qs-btn--ghost qs-btn--sm">
                  {step.link_label}
                </Link>
                {step.id === "brain_pack" && !step.done ? (
                  <button
                    type="button"
                    className="qs-btn qs-btn--primary qs-btn--sm gap-1"
                    disabled={seedBusy}
                    onClick={() => void handleSeed()}
                  >
                    {seedBusy ? (
                      <Loader2 className="size-3.5 animate-spin" aria-hidden />
                    ) : (
                      <Sparkles className="size-3.5" aria-hidden />
                    )}
                    Load starter pack
                  </button>
                ) : null}
              </div>
            </div>
          </li>
        ))}
      </ol>

      {nextStep ? (
        <p className="border-t border-(--qs-border)/50 px-4 py-3 text-xs text-cyan">
          Next: <Link href={nextStep.href} className="underline">{nextStep.link_label}</Link>
        </p>
      ) : null}
    </V4Card>
  );
}

export const SecondBrainPackWizardPanel = memo(SecondBrainPackWizardPanelInner);
SecondBrainPackWizardPanel.displayName = "SecondBrainPackWizardPanel";
