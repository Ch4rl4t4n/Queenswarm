"use client";

import Link from "next/link";
import { CheckCircle2Icon, CircleIcon, RocketIcon } from "lucide-react";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { navigateSkillFactoryTab } from "@/lib/apps-tools-routes";
import { sellableIssueLabel } from "@/lib/sellable-issue-labels";
import { cn } from "@/lib/utils";

interface LaunchReadiness {
  sellable_count: number;
  draft_count: number;
  rejected_count: number;
  gumroad_token_configured: boolean;
  gumroad_manual_ready: boolean;
}

interface NearMissRow {
  id: string;
  title: string;
  sellable_score: number;
  sellable_issues: string[];
}

interface SkillFactoryRevenueFunnelPanelProps {
  launchReadiness: LaunchReadiness | null;
  libraryCount: number;
  buildingCount: number;
  launchQueueCount: number;
  nearMiss: NearMissRow[];
  onSmartRebuild?: (id: string) => void;
  busyId?: string | null;
}

function scorePct(score: number): string {
  return `${Math.round(score * 100)}%`;
}

export function SkillFactoryRevenueFunnelPanel({
  launchReadiness,
  libraryCount,
  buildingCount,
  launchQueueCount,
  nearMiss,
  onSmartRebuild,
  busyId,
}: SkillFactoryRevenueFunnelPanelProps): JSX.Element {
  const sellable = launchReadiness?.sellable_count ?? 0;
  const drafts = launchReadiness?.draft_count ?? 0;
  const rejected = launchReadiness?.rejected_count ?? 0;
  const hasLibrary = libraryCount > 0;
  const hasSellable = sellable > 0;
  const gumroadReady = Boolean(launchReadiness?.gumroad_token_configured || launchReadiness?.gumroad_manual_ready);

  const steps = [
    {
      id: "library",
      label: "Library has skills",
      done: hasLibrary,
      detail: `${libraryCount} in library`,
      action: () => navigateSkillFactoryTab("library"),
      actionLabel: "Library",
    },
    {
      id: "sellable",
      label: "Sellable harness tier",
      done: hasSellable,
      detail: `${sellable} sellable · ${drafts} draft · ${rejected} rejected`,
      action: () => navigateSkillFactoryTab("library"),
      actionLabel: "Fix drafts",
    },
    {
      id: "launch",
      label: "Launch queue ready",
      done: launchQueueCount > 0,
      detail: `${launchQueueCount} recommended for Gumroad`,
      action: () => navigateSkillFactoryTab("launch"),
      actionLabel: "Launch",
    },
    {
      id: "gumroad",
      label: "Gumroad upload",
      done: gumroadReady && hasSellable,
      detail: gumroadReady ? "Manual or API ready" : "Set token or manual upload",
      action: () => navigateSkillFactoryTab("launch"),
      actionLabel: "Export pack",
    },
  ];

  const doneCount = steps.filter((s) => s.done).length;
  const progress = Math.round((100 * doneCount) / steps.length);

  return (
    <V4Card className="border-pollen/30 bg-pollen/5">
      <V4CardHeader
        kicker="Revenue pipeline"
        title="Sellable harness funnel"
        description="Verified niche harness — SKILL + HARNESS + EVAL + LISTING. Smart rebuild fixes rejected drafts."
        actions={
          <V4Badge tone={hasSellable ? "ok" : "warn"}>
            <RocketIcon className="mr-1 inline size-3" aria-hidden />
            {progress}%
          </V4Badge>
        }
      />
      <div className="mx-4 mb-3 h-1.5 overflow-hidden rounded-full bg-black/40">
        <div className="h-full rounded-full bg-pollen transition-[width]" style={{ width: `${progress}%` }} />
      </div>
      <ul className="space-y-2 px-4 pb-3">
        {steps.map((step) => (
          <li key={step.id} className="flex items-start gap-2 text-sm">
            {step.done ? (
              <CheckCircle2Icon className="mt-0.5 size-4 shrink-0 text-success" aria-hidden />
            ) : (
              <CircleIcon className="mt-0.5 size-4 shrink-0 text-(--qs-text-4)" aria-hidden />
            )}
            <div className="min-w-0 flex-1">
              <span className="font-medium text-(--qs-text)">{step.label}</span>
              <span className="ml-2 text-xs text-(--qs-text-4)">{step.detail}</span>
              {!step.done ? (
                <button type="button" className="ml-2 text-xs text-cyan underline" onClick={step.action}>
                  {step.actionLabel} →
                </button>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
      {buildingCount > 0 ? (
        <p className="px-4 pb-2 text-xs text-cyan">{buildingCount} factory build{buildingCount === 1 ? "" : "s"} in progress…</p>
      ) : null}
      {nearMiss.length > 0 && !hasSellable ? (
        <div className="border-t border-(--qs-border)/40 px-4 py-3">
          <p className="text-xs font-semibold uppercase text-(--qs-text-3)">Closest to launch</p>
          <ul className="mt-2 space-y-2">
            {nearMiss.slice(0, 3).map((row) => (
              <li key={row.id} className="rounded-lg border border-(--qs-border-2) px-3 py-2 text-xs">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-(--qs-text-2)">{row.title}</span>
                  <V4Badge tone="info">{scorePct(row.sellable_score)}</V4Badge>
                </div>
                {row.sellable_issues.length > 0 ? (
                  <p className="mt-1 text-(--qs-text-4)">
                    {row.sellable_issues.slice(0, 2).map(sellableIssueLabel).join(" · ")}
                  </p>
                ) : null}
                {onSmartRebuild ? (
                  <button
                    type="button"
                    className={cn("mt-2 qs-btn qs-btn--primary qs-btn--sm")}
                    disabled={busyId === row.id}
                    onClick={() => onSmartRebuild(row.id)}
                  >
                    Smart rebuild
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <p className="px-4 pb-4 text-[11px] text-(--qs-text-4)">
        Bundle: SKILL.md · HARNESS.md · EVAL_REPORT.md · LISTING.md · TOOLS.json ·{" "}
        <Link href="/manual#skill-factory" className="text-cyan underline">
          operator manual
        </Link>
      </p>
    </V4Card>
  );
}
