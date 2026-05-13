"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type {
  WorkflowDagStep,
  WorkflowFeatured,
  WorkflowListItem,
  WorkflowsDashboardResponse,
} from "@/lib/hive-types";
import { cn } from "@/lib/utils";

function formatWfAgo(sec: number): string {
  if (sec < 60) {
    return `${sec}s`;
  }
  const m = Math.floor(sec / 60);
  if (m < 120) {
    return `${m}m`;
  }
  const h = Math.floor(m / 60);
  return `${h}h`;
}

function laneBarClass(lane: string): string {
  const L = lane.toLowerCase();
  if (L === "scout") {
    return "bg-cyan";
  }
  if (L === "eval") {
    return "bg-pollen";
  }
  if (L === "sim") {
    return "bg-alert";
  }
  return "bg-success";
}

function connectorClass(prevTone: WorkflowDagStep["hex_tone"], dashedTail: boolean): string {
  const map: Record<WorkflowDagStep["hex_tone"], string> = {
    cyan: "from-cyan/90 to-cyan/15",
    pollen: "from-pollen/90 to-pollen/20",
    alert: "from-alert/90 to-alert/20",
    success: "from-success/90 to-success/20",
  };
  const grad = map[prevTone] ?? map.cyan;
  if (dashedTail) {
    return "h-px min-w-[1.25rem] shrink-0 border-t border-dotted border-zinc-600 opacity-80";
  }
  return cn("h-1 min-w-[1.25rem] shrink-0 rounded-full bg-gradient-to-r", grad);
}

function DagNode({ step }: { step: WorkflowDagStep }) {
  const base =
    "hive-hex-clip-flat relative flex h-14 w-12 shrink-0 items-center justify-center border-[6px] font-[family-name:var(--font-poppins)] text-[11px] font-bold tabular-nums transition";

  const toneOutline: Record<WorkflowDagStep["hex_tone"], string> = {
    cyan: "border-cyan/85 bg-transparent text-cyan shadow-[0_0_12px_rgb(0_255_255/0.25)]",
    pollen: "border-pollen/85 bg-transparent text-pollen shadow-[0_0_12px_rgb(255_184_0/0.22)]",
    alert: "border-alert/85 bg-transparent text-alert shadow-[0_0_12px_rgb(255_0_170/0.22)]",
    success: "border-success/85 bg-transparent text-success shadow-[0_0_12px_rgb(0_255_136/0.2)]",
  };

  const toneSolid: Record<WorkflowDagStep["hex_tone"], string> = {
    cyan: "border-cyan bg-cyan text-black shadow-[0_0_16px_rgb(0_255_255/0.45)]",
    pollen: "border-pollen bg-pollen text-black shadow-[0_0_16px_rgb(255_184_0/0.4)]",
    alert: "border-alert bg-alert text-white shadow-[0_0_16px_rgb(255_0_170/0.42)]",
    success: "border-success bg-success text-black shadow-[0_0_14px_rgb(0_255_136/0.38)]",
  };

  if (step.dag_state === "failed") {
    return (
      <div className={cn(base, "border-danger bg-danger/15 text-danger")} title={step.description_excerpt}>
        {step.step_order}
      </div>
    );
  }

  if (step.dag_state === "upcoming") {
    return (
      <div className={cn(base, toneOutline[step.hex_tone])} title={step.description_excerpt}>
        {step.step_order}
      </div>
    );
  }

  return (
    <div
      className={cn(base, toneSolid[step.hex_tone], step.dag_state === "active" && "ring-2 ring-white/40 ring-offset-2 ring-offset-[#0c0c14]")}
      title={step.description_excerpt}
    >
      {step.dag_state === "active" ? (
        <>
          <span className="opacity-0">{step.step_order}</span>
          <span className="absolute h-2 w-2 rounded-full bg-white shadow-[0_0_8px_#fff]" aria-hidden />
        </>
      ) : (
        step.step_order
      )}
    </div>
  );
}

function FeaturedCard({
  featured,
  busy,
  onPause,
  onCancel,
}: {
  featured: WorkflowFeatured;
  busy: boolean;
  onPause: () => void;
  onCancel: () => void;
}) {
  const st = featured.ui_status.toLowerCase();
  const canControl = st === "running" || st === "pending" || st === "paused";

  const badgeDot =
    st === "running"
      ? "bg-success shadow-[0_0_6px_rgb(0_255_136/0.55)]"
      : st === "completed"
        ? "bg-cyan shadow-[0_0_6px_rgb(0_255_255/0.4)]"
        : st === "paused"
          ? "bg-pollen shadow-[0_0_6px_rgb(255_184_0/0.4)]"
          : "bg-zinc-500";

  const steps = featured.steps ?? [];

  return (
    <article className="rounded-3xl qs-rim bg-[#0a0a14]/95 p-5 md:p-7">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h3 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#fafafa] md:text-xl">{featured.title}</h3>
          <p className="mt-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-500">
            {featured.short_id}
            {featured.tags.length > 0 ? ` · ${featured.tags.join(" · ")}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:justify-end">
          <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-black/50 px-3 py-1 font-[family-name:var(--font-inter)] text-xs font-semibold capitalize text-zinc-200">
            <span className={cn("h-1.5 w-1.5 rounded-full", badgeDot)} aria-hidden />
            {st}
          </span>
        </div>
      </header>

      {steps.length > 0 ? (
        <div className="mt-8 overflow-x-auto pb-2">
          <div className="flex min-w-min items-center px-1">
            {steps.map((step, i) => {
              const prev = i > 0 ? steps[i - 1] : null;
              const dashedTail = i > 0 && i === steps.length - 1 && step.dag_state === "upcoming";
              return (
                <div key={step.id} className="flex items-center">
                  {prev ? <div className={connectorClass(prev.hex_tone, dashedTail)} aria-hidden /> : null}
                  <div className="flex flex-col items-center gap-2 px-1">
                    <DagNode step={step} />
                    <span className="max-w-[4.5rem] text-center font-[family-name:var(--font-jetbrains-mono)] text-[9px] font-semibold uppercase tracking-wide text-zinc-500">
                      {step.label}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <p className="mt-6 text-sm text-zinc-600">Žiadne kroky v tomto workflow.</p>
      )}

      <footer className="mt-8 flex flex-col gap-4 border-t border-white/[0.06] pt-5 sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-xl font-[family-name:var(--font-inter)] text-xs leading-relaxed text-zinc-400">{featured.footer_line}</p>
        <div className="flex flex-wrap gap-2 sm:shrink-0">
          <button type="button" disabled={!canControl || busy} onClick={onPause} className="qs-btn qs-btn--ghost qs-btn--sm">
            Pause
          </button>
          <button type="button" disabled={!canControl || busy} onClick={onCancel} className="qs-btn qs-btn--danger qs-btn--sm">
            Cancel
          </button>
        </div>
      </footer>
    </article>
  );
}

function ListRow({
  row,
  onOpen,
  accent,
}: {
  row: WorkflowListItem;
  onOpen: (id: string) => void;
  accent: string;
}) {
  const st = row.ui_status.toLowerCase();
  const fill = st === "completed" ? "bg-pollen" : accent;

  return (
    <li className="relative overflow-hidden rounded-2xl qs-rim bg-[#0c0c12]/95 pl-1.5 pr-4 py-4 sm:pr-5">
      <div className={cn("absolute bottom-0 left-0 top-0 w-1 rounded-l-2xl", accent)} aria-hidden />
      <div className="flex flex-col gap-4 pl-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
            <p className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-[#fafafa]">{row.title}</p>
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-500">{row.short_id}</span>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            {row.tags.map((t) => (
              <span
                key={t}
                className="rounded-full border border-pollen/45 bg-pollen/[0.06] px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase tracking-wide text-pollen"
              >
                {t}
              </span>
            ))}
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-500">
              pred {formatWfAgo(row.seconds_ago)} · {row.steps_done}/{row.steps_total} krokov
            </span>
          </div>
        </div>
        <div className="flex flex-col items-stretch gap-2 sm:w-44 sm:items-end">
          <span className="font-[family-name:var(--font-inter)] text-[11px] capitalize text-zinc-500">{st}</span>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-black/60 sm:max-w-[11rem]">
            <div className={cn("h-full rounded-full transition-all", fill)} style={{ width: `${row.progress_pct}%` }} />
          </div>
          <div className="flex items-center justify-between gap-3 sm:w-full sm:max-w-[11rem]">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-sm font-bold text-pollen">{row.progress_pct}%</span>
            <button
              type="button"
              onClick={() => onOpen(row.id)}
              className="rounded-lg border border-white/20 px-3 py-1 font-[family-name:var(--font-inter)] text-[11px] font-semibold text-zinc-200 transition hover:border-pollen/40 hover:text-pollen"
            >
              Open
            </button>
          </div>
        </div>
      </div>
    </li>
  );
}

export function WorkflowsSection() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const focusId = searchParams.get("wf");

  const [data, setData] = useState<WorkflowsDashboardResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const q =
      focusId && focusId.length > 10
        ? `dashboard/workflows?limit=60&focus=${encodeURIComponent(focusId)}`
        : "dashboard/workflows?limit=60";
    try {
      const body = await hiveGet<WorkflowsDashboardResponse>(q);
      setData(body);
      setErr(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Workflow board unreachable";
      setErr(msg);
      setData(null);
    }
  }, [focusId]);

  useEffect(() => {
    void load();
    const id = window.setInterval(() => void load(), 50_000);
    return () => window.clearInterval(id);
  }, [load]);

  const setWorkflowFocus = (id: string) => {
    const next = new URLSearchParams(searchParams.toString());
    next.set("wf", id);
    router.push(`${pathname}?${next.toString()}`, { scroll: false });
  };

  const onPauseFeatured = async () => {
    if (!data?.featured) {
      return;
    }
    setBusyId(data.featured.id);
    try {
      await hivePostJson<{ ok: boolean }>(`operator/workflows/${data.featured.id}/pause`, {});
      toast.success("Workflow pozastavený.");
      await load();
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Pause zlyhal";
      toast.error(msg);
    } finally {
      setBusyId(null);
    }
  };

  const onCancelFeatured = async () => {
    if (!data?.featured) {
      return;
    }
    setBusyId(data.featured.id);
    try {
      await hivePostJson<{ ok: boolean }>(`operator/workflows/${data.featured.id}/cancel`, {});
      toast.success("Workflow zrušený.");
      await load();
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Cancel zlyhal";
      toast.error(msg);
    } finally {
      setBusyId(null);
    }
  };

  const listRows = useMemo(() => data?.workflows ?? [], [data]);

  if (err) {
    return (
      <section id="hive-workflows" className="scroll-mt-24 rounded-3xl border border-danger/30 bg-danger/[0.06] p-6">
        <p className="text-sm text-danger">Workflows: {err}</p>
      </section>
    );
  }

  if (!data) {
    return (
      <section id="hive-workflows" className="scroll-mt-24 space-y-4">
        <div className="h-10 w-48 animate-pulse rounded-lg bg-white/10" />
        <div className="h-48 animate-pulse rounded-3xl bg-white/[0.04]" />
        <div className="h-24 animate-pulse rounded-2xl bg-white/[0.04]" />
      </section>
    );
  }

  return (
    <section id="hive-workflows" className="scroll-mt-24 flex flex-col gap-8">
      <div>
        <h2 className="font-[family-name:var(--font-poppins)] text-2xl font-bold text-[#fafafa] md:text-3xl">Workflows</h2>
        <p className="mt-2 font-[family-name:var(--font-inter)] text-sm text-zinc-500">
          DAG executions · auto-decomposed from tasks
        </p>
      </div>

      {data.featured ? (
        <FeaturedCard
          featured={data.featured}
          busy={busyId === data.featured.id}
          onPause={() => void onPauseFeatured()}
          onCancel={() => void onCancelFeatured()}
        />
      ) : (
        <p className="rounded-2xl border border-dashed border-white/10 py-12 text-center text-sm text-zinc-500">Zatiaľ žiadne workflow záznamy.</p>
      )}

      <div>
        <h3 className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-zinc-400">Recent</h3>
        <ul className="mt-4 flex flex-col gap-3">
          {listRows.length === 0 ? (
            <li className="rounded-2xl border border-dashed border-white/10 py-10 text-center text-sm text-zinc-600">Žiadne položky.</li>
          ) : (
            listRows.map((row) => (
              <ListRow key={row.id} row={row} accent={laneBarClass(row.lane)} onOpen={setWorkflowFocus} />
            ))
          )}
        </ul>
      </div>
    </section>
  );
}
