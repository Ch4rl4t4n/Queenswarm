"use client";

import {
  FileTextIcon,
  Loader2Icon,
  PlayIcon,
  RefreshCwIcon,
  SquareIcon,
  Trash2Icon,
  XIcon,
} from "lucide-react";

import { V4Badge } from "@/components/ui/v4";
import { cn } from "@/lib/utils";

export interface FactoryQueueOpportunityRow {
  id: string;
  niche: string;
  title: string;
  rationale?: string;
  composite_score?: number;
  suggested_price_eur_cents?: number;
  status: string;
  supervisor_session_id: string | null;
  supervisor_session_status: string | null;
  supervisor_session_error?: string | null;
  forge_suggestion_id: string | null;
  forge_review_status?: string | null;
  forge_quality_passed?: boolean | null;
  forge_critic_approved?: boolean | null;
  forge_issues?: string[];
  progress_phase?: string;
  progress_label?: string;
  progress_detail?: string | null;
}

const ACTIVE_SESSION_STATUSES = new Set(["running", "queued", "needs_input", "paused"]);

const PHASE_STEPS = ["queued", "building", "forge_review", "completed"] as const;

function shortOppId(id: string): string {
  return `F-${id.replace(/-/g, "").slice(-4).toUpperCase()}`;
}

export function isStuckFactoryBuild(row: FactoryQueueOpportunityRow): boolean {
  return row.status === "building" && !row.supervisor_session_id;
}

function forgeNeedsRebuild(row: FactoryQueueOpportunityRow): boolean {
  return (
    row.status === "awaiting_forge"
    && (row.forge_quality_passed === false || row.forge_critic_approved === false)
  );
}

export function opportunityStatusLabel(row: FactoryQueueOpportunityRow): string {
  if (isStuckFactoryBuild(row)) return "stuck";
  if (row.status === "building") return "building";
  if (forgeNeedsRebuild(row)) return "needs rebuild";
  if (row.status === "awaiting_forge") return "forge review";
  if (row.status === "queued") return "queued";
  if (row.status === "failed") return "failed";
  return row.status;
}

function statusTone(row: FactoryQueueOpportunityRow): "ok" | "warn" | "err" | "info" | "purple" | "gold" {
  if (row.status === "failed" || isStuckFactoryBuild(row)) return "err";
  if (row.status === "building") return "info";
  if (forgeNeedsRebuild(row)) return "warn";
  if (row.status === "awaiting_forge") return "gold";
  if (row.status === "queued") return "purple";
  return "warn";
}

function resolvePhase(row: FactoryQueueOpportunityRow): string {
  if (row.progress_phase) return row.progress_phase;
  if (row.status === "building") return "building";
  if (forgeNeedsRebuild(row)) return "forge_failed";
  if (row.status === "awaiting_forge") return "forge_review";
  if (row.status === "queued") return "queued";
  if (row.status === "failed") return "failed";
  return row.status;
}

function phaseStepIndex(phase: string): number {
  if (phase === "building") return 1;
  if (phase === "forge_review" || phase === "forge_failed") return 2;
  if (phase === "completed") return 3;
  if (phase === "failed" || phase === "blocked") return -1;
  return 0;
}

function progressHeadline(row: FactoryQueueOpportunityRow): string {
  if (row.progress_label) return row.progress_label;
  if (row.supervisor_session_error) return row.supervisor_session_error.slice(0, 160);
  if (row.status === "building") return `Supervisor: ${row.supervisor_session_status ?? "starting"}`;
  if (forgeNeedsRebuild(row)) return "Forge failed — waiting for auto-rebuild";
  return row.rationale?.slice(0, 120) ?? "";
}

function progressSubline(row: FactoryQueueOpportunityRow): string | null {
  if (row.progress_detail) return row.progress_detail;
  if (row.status === "building" && row.supervisor_session_status) {
    return `Session status: ${row.supervisor_session_status}`;
  }
  return null;
}

function sessionIsActive(row: FactoryQueueOpportunityRow): boolean {
  if (!row.supervisor_session_id) return false;
  const status = (row.supervisor_session_status ?? row.status).toLowerCase();
  if (row.status === "building") return true;
  return ACTIVE_SESSION_STATUSES.has(status);
}

interface FactoryQueueTaskCardProps {
  row: FactoryQueueOpportunityRow;
  busyId: string | null;
  buildDisabled: boolean;
  factoryLlmLabel?: string;
  onRun: (opportunityId: string) => void;
  onStop: (opportunityId: string, sessionId: string) => void;
  onRebuild: (opportunityId: string) => void;
  onDismiss: (opportunityId: string) => void;
  onApproveForge?: (suggestionId: string, opportunityId: string) => void;
  onRejectForge?: (opportunityId: string, suggestionId: string) => void;
  onSync?: (opportunityId: string) => void;
  onOpenReport: (sessionId: string) => void;
}

export function FactoryQueueTaskCard({
  row,
  busyId,
  buildDisabled,
  factoryLlmLabel,
  onRun,
  onStop,
  onRebuild,
  onDismiss,
  onApproveForge,
  onRejectForge,
  onSync,
  onOpenReport,
}: FactoryQueueTaskCardProps): JSX.Element {
  const busy = busyId === row.id;
  const stuck = isStuckFactoryBuild(row);
  const activeSession = sessionIsActive(row);
  const canRun = row.status === "queued" || row.status === "failed" || stuck;
  const canStop = Boolean(row.supervisor_session_id) && (row.status === "building" || activeSession);
  const canRebuild = row.status === "failed" || stuck || row.status === "awaiting_forge";
  const forgeApproveReady =
    row.status === "awaiting_forge"
    && Boolean(row.forge_suggestion_id)
    && row.forge_quality_passed !== false
    && row.forge_critic_approved !== false;
  const phase = resolvePhase(row);
  const stepIdx = phaseStepIndex(phase);
  const headline = progressHeadline(row);
  const subline = progressSubline(row);

  return (
    <div className="v4-session-row v4-session-row--pollen" data-testid="factory-queue-row">
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex flex-wrap items-center gap-2">
          <span className="font-(family-name:--font-jetbrains-mono) text-[11px] text-(--qs-text-3)">
            {shortOppId(row.id)}
          </span>
          <V4Badge tone={statusTone(row)}>{opportunityStatusLabel(row)}</V4Badge>
          {row.composite_score != null ? (
            <V4Badge tone="gold">{Math.round(row.composite_score * 100)}% score</V4Badge>
          ) : null}
          {factoryLlmLabel ? <V4Badge tone="info">{factoryLlmLabel}</V4Badge> : null}
        </div>
        <p className="v4-session-goal text-sm font-medium text-(--qs-text)" title={row.title}>
          {row.title}
        </p>
        <p className="mt-1 line-clamp-2 text-xs text-(--qs-text-3)">
          {row.niche}
          {row.supervisor_session_error ? (
            <span className="mt-1 block text-error">{row.supervisor_session_error}</span>
          ) : null}
        </p>

        <div className="mt-2 space-y-2">
          <div className="flex flex-wrap gap-1.5">
            <V4Badge tone="info">skill factory</V4Badge>
            <V4Badge tone="info">{row.status}</V4Badge>
            {row.supervisor_session_status ? (
              <V4Badge tone="purple">session: {row.supervisor_session_status}</V4Badge>
            ) : null}
            {row.forge_quality_passed != null ? (
              <V4Badge tone={row.forge_quality_passed ? "ok" : "warn"}>
                quality {row.forge_quality_passed ? "pass" : "fail"}
              </V4Badge>
            ) : null}
            {row.forge_critic_approved != null ? (
              <V4Badge tone={row.forge_critic_approved ? "ok" : "warn"}>
                critic {row.forge_critic_approved ? "approve" : "reject"}
              </V4Badge>
            ) : null}
          </div>

          <div className="max-w-lg space-y-1.5" title={headline}>
            <div className="flex items-center gap-1">
              {PHASE_STEPS.map((step, idx) => (
                <div key={step} className="flex flex-1 items-center gap-1">
                  <div
                    className={cn(
                      "h-1.5 flex-1 rounded-full",
                      stepIdx < 0 ? "bg-error/50" : idx <= stepIdx ? "bg-pollen" : "bg-(--qs-border)",
                      row.status === "building" && idx === 1 && "animate-pulse bg-cyan",
                    )}
                  />
                </div>
              ))}
            </div>
            <p className="text-xs font-medium text-(--qs-text-2)">{headline}</p>
            {subline ? <p className="text-[11px] text-(--qs-text-4)">{subline}</p> : null}
            <p className="font-mono text-[10px] uppercase tracking-wide text-(--qs-text-4)">
              phase: {phase}
              {row.status === "building" ? " · live" : ""}
            </p>
          </div>
        </div>
      </div>

      <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
        {row.supervisor_session_id ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
            onClick={() => onOpenReport(row.supervisor_session_id!)}
          >
            <FileTextIcon className="h-3.5 w-3.5" aria-hidden />
            Report
          </button>
        ) : null}
        {forgeApproveReady && onApproveForge && row.forge_suggestion_id ? (
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm"
            disabled={busy}
            onClick={() => onApproveForge(row.forge_suggestion_id!, row.id)}
          >
            Approve
          </button>
        ) : null}
        {row.status === "awaiting_forge" && row.forge_quality_passed === false && onRejectForge && row.forge_suggestion_id ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm"
            disabled={busy}
            onClick={() => onRejectForge(row.id, row.forge_suggestion_id!)}
          >
            Reject forge
          </button>
        ) : null}
        {row.status === "awaiting_forge" && row.forge_review_status === "approved" && onSync ? (
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" disabled={busy} onClick={() => onSync(row.id)}>
            Sync
          </button>
        ) : null}
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
          disabled={busy || buildDisabled || !canRun}
          title={buildDisabled ? "Run smoke test on Factory LLM first" : undefined}
          onClick={() => onRun(row.id)}
        >
          {busy && canRun ? <Loader2Icon className="h-3.5 w-3.5 animate-spin" /> : <PlayIcon className="h-3.5 w-3.5" />}
          Run
        </button>
        <button
          type="button"
          className={cn("qs-btn qs-btn--ghost qs-btn--sm gap-1.5", canStop && "text-error")}
          disabled={busy || !canStop}
          onClick={() => row.supervisor_session_id && onStop(row.id, row.supervisor_session_id)}
        >
          <SquareIcon className="h-3.5 w-3.5" aria-hidden />
          Stop
        </button>
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
          disabled={busy || buildDisabled || !canRebuild}
          onClick={() => onRebuild(row.id)}
        >
          <RefreshCwIcon className="h-3.5 w-3.5" aria-hidden />
          Rebuild
        </button>
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
          disabled={busy}
          onClick={() => onDismiss(row.id)}
          aria-label="Dismiss"
        >
          <Trash2Icon className="h-3.5 w-3.5" aria-hidden />
          Dismiss
        </button>
      </div>
    </div>
  );
}
