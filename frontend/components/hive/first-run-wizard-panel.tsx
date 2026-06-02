"use client";

import Link from "next/link";
import { CheckCircle2, Circle, Loader2, Rocket, XIcon } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { usePlatform } from "@/components/hive/platform-context";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError } from "@/lib/api";
import {
  dismissFirstRunWizard,
  isFirstRunWizardDismissed,
} from "@/lib/first-run-wizard";
import { useSoloFirstRun } from "@/lib/use-solo-first-run";

function FirstRunWizardPanelInner(): JSX.Element | null {
  const { soloMode } = usePlatform();
  const [dismissed, setDismissed] = useState(true);
  const { data, loading, briefBusy, reload, applyStarterBrief } = useSoloFirstRun({
    enabled: soloMode,
  });

  useEffect(() => {
    setDismissed(isFirstRunWizardDismissed());
  }, []);

  const handleApplyBrief = useCallback(async () => {
    try {
      const applied = await applyStarterBrief();
      if (applied) {
        toast.success("Starter PROJECT brief saved to Curated memory.");
      } else {
        toast.message("Brief already looks ready — edit in Knowledge if needed.");
      }
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Could not apply starter brief");
    }
  }, [applyStarterBrief]);

  const handleDismiss = useCallback(() => {
    dismissFirstRunWizard();
    setDismissed(true);
  }, []);

  if (!soloMode || dismissed) {
    return null;
  }

  if (loading && !data) {
    return (
      <V4Card className="border-pollen/30">
        <p className="flex items-center gap-2 p-4 text-sm text-(--qs-muted)">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading setup checklist…
        </p>
      </V4Card>
    );
  }

  if (!data?.enabled || data.complete) {
    return null;
  }

  const nextStep = data.steps.find((step) => !step.done);

  return (
    <V4Card id="first-run-wizard" className="border-pollen/35 bg-pollen/5">
      <V4CardHeader
        kicker="Setup once"
        title="First-run wizard"
        description="Three steps before your daily loop — LLM keys, project brief, first session."
        actions={
          <div className="flex gap-2">
            <HiveRefreshButton busy={loading} onClick={() => void reload()} />
            <button
              type="button"
              className="rounded-md p-1 text-(--qs-text-3) hover:text-(--qs-text)"
              aria-label="Dismiss first-run wizard"
              onClick={handleDismiss}
            >
              <XIcon className="size-4" aria-hidden />
            </button>
          </div>
        }
      />

      <div
        className="mx-4 mb-2 h-2 overflow-hidden rounded-full bg-black/40"
        role="progressbar"
        aria-valuenow={data.progress_pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="First-run setup progress"
      >
        <div
          className="h-full rounded-full bg-linear-to-r from-pollen to-cyan transition-[width] duration-500"
          style={{ width: `${data.progress_pct}%` }}
        />
      </div>
      <p className="mb-4 px-4 text-xs text-(--qs-muted)">{data.progress_pct}% complete</p>

      <ol className="space-y-3 px-4 pb-4">
        {data.steps.map((step, index) => (
          <li
            key={step.id}
            className="rounded-xl border border-(--qs-border)/60 bg-black/25 p-3"
          >
            <div className="flex flex-wrap items-start gap-3">
              {step.done ? (
                <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-[#00FF88]" aria-hidden />
              ) : (
                <Circle className="mt-0.5 size-5 shrink-0 text-pollen" aria-hidden />
              )}
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-[10px] text-(--qs-text-3)">{index + 1}</span>
                  <span className="text-sm font-semibold text-(--qs-text)">{step.label}</span>
                  {step.done ? <V4Badge tone="ok">Done</V4Badge> : null}
                  {nextStep?.id === step.id ? <V4Badge tone="warn">Next</V4Badge> : null}
                </div>
                <p className="mt-1 text-xs leading-relaxed text-(--qs-muted)">{step.detail}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Link href={step.href} className="qs-btn qs-btn--ghost qs-btn--sm">
                    {step.link_label}
                  </Link>
                  {step.id === "llm_keys" && !step.done ? (
                    <Link href="/settings/api-keys#research-keys" className="qs-btn qs-btn--ghost qs-btn--sm">
                      Optional: Tavily key
                    </Link>
                  ) : null}
                  {step.id === "project_brief" && !step.done ? (
                    <button
                      type="button"
                      className="qs-btn qs-btn--primary qs-btn--sm gap-1"
                      disabled={briefBusy}
                      onClick={() => void handleApplyBrief()}
                    >
                      {briefBusy ? (
                        <Loader2 className="size-3.5 animate-spin" aria-hidden />
                      ) : (
                        <Rocket className="size-3.5" aria-hidden />
                      )}
                      Apply starter brief
                    </button>
                  ) : null}
                </div>
              </div>
            </div>
          </li>
        ))}
      </ol>

      <p className="border-t border-(--qs-border)/40 px-4 py-3 text-[11px] text-(--qs-muted)">
        Full guide:{" "}
        <Link href="/manual#setup-once" className="text-cyan underline">
          Manual → One-time setup
        </Link>
      </p>
    </V4Card>
  );
}

export const FirstRunWizardPanel = memo(FirstRunWizardPanelInner);
