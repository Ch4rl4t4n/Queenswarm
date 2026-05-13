"use client";

import type { WorkflowRow } from "@/lib/hive-types";
import { NeonButton } from "@/components/ui/neon-button";
import { cn } from "@/lib/utils";

const STEP_META: readonly { label: string; accent: "data" | "pollen" | "alert" | "success" }[] = [
  { label: "Scrape", accent: "data" },
  { label: "Fact-check", accent: "pollen" },
  { label: "Simulate", accent: "alert" },
  { label: "Compose", accent: "success" },
  { label: "Publish", accent: "success" },
] as const;

interface WorkflowDagHeroProps {
  workflow: WorkflowRow;
}

interface HexVisualProps {
  label: string;
  state: "done" | "active" | "todo";
  accent: (typeof STEP_META)[number]["accent"];
}

const ACCENTS: Record<HexVisualProps["accent"], { fill?: string; line?: string; glow?: string }> = {
  data: {
    fill: "border-data bg-data text-black shadow-[0_0_20px_rgb(0_255_255/0.5)]",
    line: "border-data text-data shadow-[inset_0_0_0_1px_rgb(0_255_255/0.4)] bg-black/55",
    glow: "border-data shadow-[0_0_26px_rgb(0_255_255/0.35)] bg-black/30 text-data",
  },
  pollen: {
    fill: "border-pollen bg-pollen text-black shadow-[0_0_20px_rgb(255_184_0/0.48)]",
    line: "border-pollen text-pollen bg-black/55",
    glow: "border-pollen shadow-[0_0_24px_rgb(255_184_0/0.35)] bg-black/30 text-pollen",
  },
  alert: {
    fill: "border-alert bg-[rgb(255_0_170/0.18)] text-alert shadow-[0_0_24px_rgb(255_0_170/0.45)] font-bold",
    line: "border-alert text-alert bg-transparent shadow-[inset_0_0_0_2px_rgb(255_0_170/0.45)]",
    glow: "border-alert shadow-[0_0_28px_rgb(255_0_170/0.45)] bg-black/35 text-alert",
  },
  success: {
    fill: "",
    line: "border-success text-success bg-transparent opacity-95",
    glow: "border-success shadow-[0_0_22px_rgb(0_255_136/0.35)] bg-black/35 text-success",
  },
};

function DagHex({ label, state, accent }: HexVisualProps) {
  const a = ACCENTS[accent];
  const cls =
    state === "done"
      ? a.fill
      : state === "active"
        ? a.glow ?? a.line ?? ""
        : `${a.line} opacity-65`;

  return (
    <div className="flex flex-col items-center gap-3">
      <div
        className={cn(
          "hive-hex flex h-14 w-14 shrink-0 items-center justify-center border-[6px] text-[11px] font-[family-name:var(--font-jetbrains-mono)] font-semibold uppercase tracking-tighter md:h-16 md:w-16",
          cls,
          !cls && "border-cyan/[0.2] bg-black/40 text-zinc-500",
        )}
      >
        {label.slice(0, 5)}
      </div>
      <span className="hidden text-center font-[family-name:var(--font-inter)] text-[11px] text-zinc-500 md:block">{label}</span>
    </div>
  );
}

/** Horizontal DAG aligned with cockpit mock — linear states from LangGraph shards. */
export function WorkflowDagHero({ workflow }: WorkflowDagHeroProps) {
  const total = Math.max(workflow.total_steps, STEP_META.length);
  const cursor = Math.min(workflow.completed_steps, STEP_META.length - 1);

  return (
    <section className="rounded-3xl border border-cyan/[0.12] bg-hive-card/90 p-6 md:p-8">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-cyan/[0.08] pb-5">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1 rounded-full border border-success/35 bg-success/[0.1] px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.12em] text-success">
              ● Running
            </span>
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-500">{workflow.id}</span>
          </div>
          <h2 className="mt-4 font-[family-name:var(--font-space-grotesk)] text-xl font-semibold text-[#fafafa] md:text-2xl">
            {workflow.original_task_text.slice(0, 120)}
            {workflow.original_task_text.length > 120 ? "…" : ""}
          </h2>
          <p className="mt-2 font-[family-name:var(--font-inter)] text-sm text-muted-foreground">
            Step {Math.min(workflow.completed_steps + 1, total)} of {total} · Sim-01 sandboxing trade scenarios.
          </p>
        </div>
        <div className="flex gap-2">
          <NeonButton type="button" variant="ghost" className="text-xs uppercase">
            Pause
          </NeonButton>
          <NeonButton type="button" variant="danger" className="text-xs uppercase">
            Cancel
          </NeonButton>
        </div>
      </div>

      <div className="mt-10 flex flex-wrap items-center justify-center gap-2 md:flex-nowrap md:gap-0">
        {STEP_META.map((meta, i) => {
          const state: HexVisualProps["state"] =
            i < workflow.completed_steps ? "done" : i === workflow.completed_steps ? "active" : "todo";
          return (
            <div key={meta.label} className="flex flex-1 items-center justify-center">
              <DagHex label={meta.label} state={state} accent={meta.accent} />
              {i < STEP_META.length - 1 ? (
                <div
                  className={cn(
                    "mx-1 hidden h-0 min-w-[24px] flex-1 border-t-2 md:block",
                    i < cursor ? "border-success/60 border-dotted" : "border-cyan/[0.12]",
                  )}
                />
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}
