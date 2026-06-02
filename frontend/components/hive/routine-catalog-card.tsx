"use client";

import Link from "next/link";
import { CalendarClock, Play } from "lucide-react";

import { RoutineWebhookControls } from "@/components/hive/routine-webhook-controls";
import { V4Badge, V4Chip } from "@/components/ui/v4";
import type { SupervisorRoutineRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

function formatInterval(seconds: number | null): string {
  if (!seconds || seconds <= 0) {
    return "—";
  }
  if (seconds % 86_400 === 0) {
    return `every ${seconds / 86_400}d`;
  }
  if (seconds % 3_600 === 0) {
    return `every ${seconds / 3_600}h`;
  }
  if (seconds >= 60) {
    return `every ${Math.round(seconds / 60)}m`;
  }
  return `every ${seconds}s`;
}

function formatAgo(iso: string | null): string {
  if (!iso) {
    return "never";
  }
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms) || ms < 0) {
    return "—";
  }
  const min = Math.floor(ms / 60_000);
  if (min < 1) {
    return "just now";
  }
  if (min < 60) {
    return `${min}m ago`;
  }
  const h = Math.floor(min / 60);
  if (h < 48) {
    return `${h}h ago`;
  }
  return `${Math.floor(h / 24)}d ago`;
}

function statusTone(status: string, isActive: boolean): "ok" | "warn" | "err" | "info" | "gold" {
  if (!isActive) {
    return "warn";
  }
  if (status === "scheduled" || status === "active") {
    return "ok";
  }
  if (status === "error" || status === "failed") {
    return "err";
  }
  return "info";
}

export interface RoutineCatalogCardProps {
  routine: SupervisorRoutineRow;
  index: number;
  triggerBusy: boolean;
  onTrigger: (routineId: string) => void;
  className?: string;
}

/** Marketplace-style supervisor routine card — catalog layout with prominent webhook panel. */
export function RoutineCatalogCard({
  routine,
  index,
  triggerBusy,
  onTrigger,
  className,
}: RoutineCatalogCardProps): JSX.Element {
  const intervalLabel = formatInterval(routine.interval_seconds);
  const scheduleLabel =
    routine.schedule_kind === "cron" && routine.cron_expr
      ? `cron ${routine.cron_expr}`
      : intervalLabel;

  return (
    <article
      className={cn(
        "hub-catalog-card v4-routine-catalog-card v4-dream-cycle-card flex h-full min-w-0 flex-col gap-3",
        className,
      )}
    >
      <div className="flex min-w-0 items-start justify-between gap-2">
        <div className="min-w-0 flex-1 space-y-1">
          <p className="line-clamp-2 text-sm font-semibold text-(--qs-text)">{routine.name}</p>
          <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">
            #{index + 1} · {scheduleLabel} · {routine.status}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-1.5">
          <V4Badge tone={routine.is_active ? "ok" : "warn"}>{routine.is_active ? "active" : "paused"}</V4Badge>
          <V4Badge tone={statusTone(routine.status, routine.is_active)}>{routine.status}</V4Badge>
        </div>
      </div>

      <p className="line-clamp-3 text-xs leading-relaxed text-(--qs-text-2)">{routine.goal_template}</p>

      <dl className="v4-recipe-card-stats grid grid-cols-3 gap-2 border-y border-[color:var(--qs-border)]/40 py-3 text-sm">
        <div>
          <dt className="v4-field-label">Interval</dt>
          <dd className="mt-1 font-mono text-[11px] text-(--qs-text)">{intervalLabel}</dd>
        </div>
        <div>
          <dt className="v4-field-label">Last run</dt>
          <dd className="mt-1 text-[11px] text-(--qs-text-2)">{formatAgo(routine.last_run_at)}</dd>
        </div>
        <div>
          <dt className="v4-field-label">Runtime</dt>
          <dd className="mt-1 truncate font-mono text-[10px] text-(--qs-text-3)">{routine.runtime_mode}</dd>
        </div>
      </dl>

      {(routine.roles?.length ?? 0) > 0 || (routine.skills?.length ?? 0) > 0 ? (
        <div className="qs-tag-row">
          {(routine.roles ?? []).slice(0, 4).map((role) => (
            <V4Chip key={role} type="span" variant="tag">
              {role}
            </V4Chip>
          ))}
          {(routine.skills ?? []).slice(0, 3).map((skill) => (
            <V4Chip key={skill} type="span" variant="tag">
              {skill}
            </V4Chip>
          ))}
        </div>
      ) : null}

      <RoutineWebhookControls routineId={routine.id} routineName={routine.name} variant="catalog" />

      <div className="v4-dream-cycle-card-actions mt-auto flex flex-wrap gap-2 pb-1">
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm min-h-10 flex-1 justify-center gap-1.5 sm:flex-none"
          disabled={triggerBusy}
          onClick={() => onTrigger(routine.id)}
        >
          <Play className="h-3.5 w-3.5" aria-hidden />
          {triggerBusy ? "Running…" : "Run now"}
        </button>
        <Link
          href="/agents#sessions"
          className="qs-btn qs-btn--ghost qs-btn--sm min-h-10 flex-1 justify-center gap-1.5 sm:flex-none"
        >
          <CalendarClock className="h-3.5 w-3.5" aria-hidden />
          Sessions
        </Link>
        <Link href="/recipes" className="qs-btn qs-btn--primary qs-btn--sm min-h-10 w-full justify-center gap-1.5 sm:w-auto">
          Schedule from recipe
        </Link>
      </div>
    </article>
  );
}
