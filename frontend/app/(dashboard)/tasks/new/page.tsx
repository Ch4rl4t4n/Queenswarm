"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { NeonButton } from "@/components/ui/neon-button";
import { hiveGet, hivePostJson } from "@/lib/api";
import type { SubSwarmRow } from "@/lib/hive-types";

const TASK_TYPES = ["scrape", "evaluate", "simulate", "report"] as const;

interface IntakeAck {
  workflow_id?: string;
  task_id?: string;
  celery_task_id?: string | null;
  execution?: string;
}

export default function TasksNewPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [title, setTitle] = useState("Hive objective");
  const [description, setDescription] = useState("");
  const [priorityBand, setPriorityBand] = useState<"low" | "medium" | "high">("medium");
  const [taskType, setTaskType] = useState<(typeof TASK_TYPES)[number]>("scrape");
  const [swarmPick, setSwarmPick] = useState("");
  const [swarms, setSwarms] = useState<SubSwarmRow[]>([]);

  const priority = useMemo(() => {
    if (priorityBand === "high") return 2;
    if (priorityBand === "low") return 8;
    return 5;
  }, [priorityBand]);

  useEffect(() => {
    let alive = true;
    void hiveGet<SubSwarmRow[]>("/swarms?limit=50")
      .then((rows) => {
        if (alive) {
          setSwarms(rows);
        }
      })
      .catch(() => {
        if (alive) {
          setSwarms([]);
        }
      });
    return () => {
      alive = false;
    };
  }, []);

  async function onSubmit(ev: FormEvent): Promise<void> {
    ev.preventDefault();
    if (description.trim().length < 8) {
      toast.error("Describe the mission (at least 8 characters).");
      return;
    }
    setBusy(true);
    try {
      const payload: Record<string, unknown> = {
        title: title.trim(),
        task_text: description.trim(),
        task_type: taskType,
        priority,
        start_execution: true,
        defer_to_worker: true,
      };
      if (swarmPick) {
        payload.swarm_id = swarmPick;
      }
      const ack = await hivePostJson<IntakeAck>("operator/intake-task", payload);
      toast.success(`Task queued (${ack.execution ?? "unknown"})`);
      router.push("/tasks");
      router.refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Intake failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header>
        <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs uppercase tracking-[0.22em] text-data">
          Phase G · rapid intake
        </p>
        <h1 className="mt-2 font-[family-name:var(--font-space-grotesk)] text-3xl font-semibold text-pollen">
          New hive task
        </h1>
        <p className="mt-2 font-[family-name:var(--font-inter)] text-sm text-zinc-500">
          Auto Workflow Breaker plus Celery handoff via POST <code className="text-data">operator/intake-task</code>.
        </p>
      </header>

      <form
        onSubmit={(e) => void onSubmit(e)}
        className="space-y-6 rounded-3xl border border-cyan/[0.08] bg-hive-card/90 p-6 neon-border-pg lg:p-8"
      >
        <label className="block space-y-2">
          <span className="font-[family-name:var(--font-inter)] text-sm text-[#fafafa]">Mission title</span>
          <input
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-xl border border-white/[0.08] bg-black/45 px-4 py-3 font-[family-name:var(--font-inter)] text-sm text-[#fafafa]"
          />
        </label>
        <label className="block space-y-2">
          <span className="font-[family-name:var(--font-inter)] text-sm text-[#fafafa]">Detailed brief</span>
          <textarea
            required
            minLength={8}
            rows={6}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full rounded-xl border border-white/[0.08] bg-black/45 px-4 py-3 font-[family-name:var(--font-inter)] text-sm text-[#fafafa]"
            placeholder="Describe outcomes, guardrails, and sources for scouts…"
          />
        </label>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2">
            <span className="text-sm text-[#fafafa]">Routing type</span>
            <select
              value={taskType}
              onChange={(e) => setTaskType(e.target.value as (typeof TASK_TYPES)[number])}
              className="w-full rounded-xl border border-white/[0.08] bg-black/45 px-3 py-2 text-sm text-[#fafafa]"
            >
              {TASK_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-sm text-[#fafafa]">Priority</span>
            <select
              value={priorityBand}
              onChange={(e) => setPriorityBand(e.target.value as typeof priorityBand)}
              className="w-full rounded-xl border border-white/[0.08] bg-black/45 px-3 py-2 text-sm text-[#fafafa]"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </label>
        </div>
        <label className="block space-y-2">
          <span className="text-sm text-[#fafafa]">Swarm preference (optional UUID)</span>
          <select
            value={swarmPick}
            onChange={(e) => setSwarmPick(e.target.value)}
            className="w-full rounded-xl border border-white/[0.08] bg-black/45 px-3 py-2 text-sm text-[#fafafa]"
          >
            <option value="">Auto-route (breaker picks colony)</option>
            {swarms.map((sw) => (
              <option key={sw.id} value={sw.id}>
                {sw.name} · {sw.purpose}
              </option>
            ))}
          </select>
        </label>

        <div className="flex flex-wrap gap-3">
          <NeonButton type="submit" variant="primary" disabled={busy}>
            {busy ? "Enqueueing…" : "Submit to swarm"}
          </NeonButton>
          <NeonButton asChild variant="ghost">
            <Link href="/tasks">Cancel</Link>
          </NeonButton>
        </div>
      </form>
    </div>
  );
}
