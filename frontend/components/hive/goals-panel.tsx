"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

interface GoalRow {
  id: string;
  title: string;
  status: string;
  current_iteration: number;
  max_iterations: number;
  budget_usd: number;
  spent_usd: number;
}

function statusTone(status: string): "ok" | "warn" | "info" | "err" {
  const s = status.toLowerCase();
  if (s.includes("complete")) return "ok";
  if (s.includes("fail") || s.includes("halt")) return "err";
  if (s.includes("run") || s.includes("active")) return "info";
  return "warn";
}

/** Queen goal orchestration list + quick create. */
export function GoalsPanel() {
  const [rows, setRows] = useState<GoalRow[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const data = await hiveGet<GoalRow[]>("goals?limit=30");
      setRows(data);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Goals unavailable");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function createGoal() {
    const trimmed = title.trim();
    if (trimmed.length < 3) {
      toast.error("Goal title must be at least 3 characters");
      return;
    }
    setBusy(true);
    try {
      await hivePostJson("goals", {
        title: trimmed,
        description_md: description.trim(),
        acceptance_criteria_md: "",
        max_iterations: 3,
        budget_usd: 0,
      });
      toast.success("Goal queued for execution");
      setTitle("");
      setDescription("");
      await reload();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <V4Card>
        <V4CardHeader title="New goal" description="Queen orchestrator — decomposes into tasks and audits until done." />
        <div className="grid gap-3 md:grid-cols-2">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Goal title"
            className="qs-input"
          />
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Description (optional)"
            className="qs-input"
          />
        </div>
        <div className="mt-3 flex justify-end">
          <button type="button" className="qs-btn qs-btn--primary qs-btn--sm gap-2" disabled={busy} onClick={() => void createGoal()}>
            <Plus className="h-4 w-4" aria-hidden />
            Create goal
          </button>
        </div>
      </V4Card>

      <V4Card>
        <V4CardHeader title="Active goals" description="Tenant-scoped Queen `/goal` orchestration runs." />
        {err ? <p className="mb-3 text-sm text-(--qs-red)">{err}</p> : null}
        <div className="flex flex-col gap-3">
          {!rows.length ? (
            <p className="text-sm text-(--qs-text-3)">No goals yet.</p>
          ) : (
            rows.map((row) => (
              <div key={row.id} className="v4-recent-task-row">
                <V4Badge tone={statusTone(row.status)}>{row.status.replaceAll("_", " ")}</V4Badge>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-(--qs-text)">{row.title}</div>
                  <div className="mt-0.5 text-xs text-(--qs-text-3)">
                    iter {row.current_iteration}/{row.max_iterations} · ${row.spent_usd.toFixed(2)} / ${row.budget_usd.toFixed(2)}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </V4Card>
    </div>
  );
}
