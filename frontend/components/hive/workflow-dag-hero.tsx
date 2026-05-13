"use client";

import type { WorkflowRow } from "@/lib/hive-types";
import { HexNumberBadge } from "@/components/hive/hex-metric-tile";
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

const ACCENT_HEX: Record<HexVisualProps["accent"], string> = {
  data: "#00E5FF",
  pollen: "#FFB800",
  alert: "#FF00AA",
  success: "#00FF88",
};

function DagHex({ label, state, accent }: HexVisualProps) {
  const stroke = ACCENT_HEX[accent];
  return (
    <div className="flex flex-col items-center gap-3">
      <div className={cn(state === "todo" && "opacity-[0.72] saturate-[0.75]")}>
        <HexNumberBadge
          value={label.slice(0, 5)}
          monoLabel
          strokeColor={stroke}
          glowColor={state === "active" || state === "done" ? stroke : undefined}
          variant={state === "done" ? "solid" : "default"}
          sizePx={state === "active" ? 60 : 56}
        />
      </div>
      <span className="hidden text-center font-[family-name:var(--font-poppins)] text-[11px] text-zinc-500 md:block">{label}</span>
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
            <span className="inline-flex items-center gap-1 rounded-full border border-success/35 bg-success/[0.1] px-2 py-0.5 qs-chip uppercase tracking-[0.06em] text-success">
              ● Running
            </span>
            <span className="font-[family-name:var(--font-poppins)] text-[11px] text-zinc-500">{workflow.id}</span>
          </div>
          <h2 className="mt-4 font-[family-name:var(--font-poppins)] text-xl font-semibold text-[#fafafa] md:text-2xl">
            {workflow.original_task_text.slice(0, 120)}
            {workflow.original_task_text.length > 120 ? "…" : ""}
          </h2>
          <p className="mt-2 font-[family-name:var(--font-poppins)] text-sm text-muted-foreground">
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
