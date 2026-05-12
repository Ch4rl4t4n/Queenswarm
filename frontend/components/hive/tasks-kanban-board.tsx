"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import type { TaskRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

type ColumnKey = "queued" | "running" | "completed" | "failed";

const COLUMNS: { key: ColumnKey; label: string; tint: string }[] = [
  { key: "queued", label: "Queued", tint: "border-pollen/35 text-pollen" },
  { key: "running", label: "Running", tint: "border-success/35 text-success" },
  { key: "completed", label: "Completed", tint: "border-data/35 text-data" },
  { key: "failed", label: "Failed", tint: "border-danger/40 text-danger" },
];

function columnFor(statusRaw: string): ColumnKey {
  const s = statusRaw.toUpperCase();
  if (s.includes("RUN")) return "running";
  if (s.includes("COMP")) return "completed";
  if (s.includes("FAIL") || s.includes("CANCEL")) return "failed";
  return "queued";
}

interface TasksKanbanBoardProps {
  tasks: TaskRow[];
}

export function TasksKanbanBoard({ tasks }: TasksKanbanBoardProps) {
  const [swarmNeedle, setSwarmNeedle] = useState("");
  const [q, setQ] = useState("");

  const filtered = useMemo(() => {
    const sn = swarmNeedle.trim().toLowerCase();
    const nq = q.trim().toLowerCase();
    return tasks.filter((t) => {
      const swarmOk = sn === "" || (t.swarm_id ?? "").toLowerCase().includes(sn);
      const textOk = nq === "" || `${t.title} ${t.task_type} ${t.id}`.toLowerCase().includes(nq);
      return swarmOk && textOk;
    });
  }, [tasks, swarmNeedle, q]);

  const grouped = useMemo(() => {
    const init: Record<ColumnKey, TaskRow[]> = { queued: [], running: [], completed: [], failed: [] };
    for (const t of filtered) {
      init[columnFor(t.status)].push(t);
    }
    return init;
  }, [filtered]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap gap-2 font-[family-name:var(--font-jetbrains-mono)] text-xs text-zinc-500">
          <span className="rounded-full border border-cyan/[0.12] px-3 py-1">
            Hive Kanban · {filtered.length}/{tasks.length} visible
          </span>
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row">
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search title / type…"
            className="min-w-0 flex-1 rounded-xl border border-cyan/[0.15] bg-black/45 px-4 py-2 font-[family-name:var(--font-inter)] text-sm text-[#fafafa] placeholder:text-zinc-500 focus:border-pollen/35 focus:outline-none"
          />
          <input
            value={swarmNeedle}
            onChange={(e) => setSwarmNeedle(e.target.value)}
            placeholder="Filter swarm UUID fragment…"
            className="min-w-[200px] rounded-xl border border-cyan/[0.15] bg-black/45 px-4 py-2 font-[family-name:var(--font-inter)] text-sm text-[#fafafa] placeholder:text-zinc-500 focus:border-pollen/35 focus:outline-none"
          />
        </div>
        <NeonTasksNew />
      </div>

      <div className="grid gap-4 lg:grid-cols-4">
        {COLUMNS.map((col) => (
          <section
            key={col.key}
            className={`flex max-h-[70vh] flex-col rounded-2xl border bg-hive-card/90 p-3 shadow-inner hive-scrollbar ${col.tint}`}
          >
            <header className="mb-3 flex shrink-0 items-center justify-between border-b border-white/[0.06] pb-2">
              <span className="font-[family-name:var(--font-space-grotesk)] text-sm font-semibold uppercase tracking-[0.12em]">
                {col.label}
              </span>
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-500">
                {grouped[col.key].length}
              </span>
            </header>
            <ul className="flex flex-1 flex-col gap-2 overflow-y-auto pr-1">
              {grouped[col.key].map((t) => (
                <li
                  key={t.id}
                  className="rounded-xl border border-cyan/[0.08] bg-black/35 p-3 transition hover:border-pollen/30"
                >
                  <p className="font-[family-name:var(--font-inter)] text-sm font-medium text-[#fafafa]">{t.title}</p>
                  <div className="mt-2 flex flex-wrap gap-2 font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.14em] text-zinc-500">
                    <span>{t.task_type}</span>
                    <span>p{t.priority}</span>
                    <span>{t.agent_id ? `bee ${String(t.agent_id).slice(0, 8)}` : "unassigned"}</span>
                  </div>
                  {t.created_at ? (
                    <p className="mt-2 font-[family-name:var(--font-inter)] text-[11px] text-zinc-600">
                      {new Date(t.created_at).toLocaleString()}
                    </p>
                  ) : null}
                  <ConfidenceHint result={t.result} />
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}

function ConfidenceHint({ result }: { result?: TaskRow["result"] }) {
  if (!result || typeof result !== "object") {
    return null;
  }
  const raw = "confidence_pct" in result ? (result as { confidence_pct?: unknown }).confidence_pct : undefined;
  const pct = typeof raw === "number" ? raw : null;
  if (pct === null) {
    return null;
  }
  return (
    <p className="mt-2 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-data">
      confidence {pct.toFixed(1)}%
    </p>
  );
}

function NeonTasksNew(): JSX.Element {
  return (
    <Link
      href="/tasks/new"
      className={cn(
        "inline-flex items-center justify-center rounded-full border border-pollen bg-pollen px-4 py-2",
        "font-[family-name:var(--font-space-grotesk)] text-xs font-semibold uppercase tracking-[0.16em] text-black",
        "glow-amber transition hover:bg-[#ffc933]",
      )}
    >
      + New Task
    </Link>
  );
}
