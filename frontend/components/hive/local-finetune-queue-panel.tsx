"use client";

import { CpuIcon, Loader2Icon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

interface FinetuneJobRow {
  id: string;
  status: string;
  adapter_name: string;
  base_model: string;
  dataset_row_count: number;
  training_plan_summary: string;
}

interface FinetuneQueueSnapshot {
  enabled: boolean;
  gpu_worker_enabled: boolean;
  execute_mode: boolean;
  jobs: FinetuneJobRow[];
  operator_hint: string;
}

/** Settings panel — GPU fine-tune job queue with HITL approve (Track M LOC9). */
export function LocalFinetuneQueuePanel(): JSX.Element | null {
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [disabled, setDisabled] = useState(false);
  const [snapshot, setSnapshot] = useState<FinetuneQueueSnapshot | null>(null);
  const [adapterName, setAdapterName] = useState("");
  const [baseModel, setBaseModel] = useState("qwen2.5:7b");

  const load = useCallback(async () => {
    try {
      const body = await hiveGet<FinetuneQueueSnapshot>("llm-routing/finetune-jobs");
      setSnapshot(body);
      setDisabled(false);
    } catch (e) {
      if (e instanceof HiveApiError && e.status === 404) {
        setDisabled(true);
      } else {
        toast.error(e instanceof HiveApiError ? e.message : "Fine-tune queue unavailable.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const createDraft = useCallback(async () => {
    if (!adapterName.trim()) {
      toast.error("Adapter name required.");
      return;
    }
    setBusyId("create");
    try {
      await hivePostJson("llm-routing/finetune-jobs", {
        adapter_name: adapterName.trim(),
        base_model: baseModel.trim() || "qwen2.5:7b",
        dataset_source: "verified_export",
        epochs: 1,
      });
      toast.success("Fine-tune job draft created — approve to enqueue GPU worker.");
      setAdapterName("");
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Create job failed.");
    } finally {
      setBusyId(null);
    }
  }, [adapterName, baseModel, load]);

  const approve = useCallback(
    async (jobId: string) => {
      setBusyId(jobId);
      try {
        await hivePostJson(`llm-routing/finetune-jobs/${jobId}/approve`, {});
        toast.success("Job approved — GPU worker queued.");
        await load();
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Approve failed.");
      } finally {
        setBusyId(null);
      }
    },
    [load],
  );

  if (disabled) {
    return null;
  }

  if (loading) {
    return (
      <V4Card className="mt-6">
        <div className="flex items-center gap-2 p-4 text-sm text-(--qs-text-3)">
          <Loader2Icon className="size-4 animate-spin" aria-hidden />
          Loading fine-tune queue…
        </div>
      </V4Card>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  return (
    <div data-testid="local-finetune-queue-panel">
      <V4Card className="mt-6 border-cyan/25">
        <V4CardHeader
          title="Fine-tune queue · GPU worker"
          description={
            snapshot.execute_mode
              ? "Execute mode ON — host Unsloth script runs on gpu_finetune worker."
              : "Simulation mode — worker validates dataset and emits training plan."
          }
          leadingIcon={CpuIcon}
          leadingIconTone="cyan"
          actions={
            snapshot.gpu_worker_enabled ? (
              <V4Badge tone="info">gpu_finetune</V4Badge>
            ) : (
              <V4Badge tone="warn">worker off</V4Badge>
            )
          }
        />
        <p className="px-4 pb-3 text-xs text-(--qs-text-3)">{snapshot.operator_hint}</p>
        <div className="flex flex-wrap gap-2 px-4 pb-4">
          <input
            type="text"
            placeholder="Adapter name (e.g. qs-v1)"
            value={adapterName}
            onChange={(e) => setAdapterName(e.target.value)}
            className="min-w-[160px] flex-1 rounded-md border border-(--qs-border-subtle) bg-(--qs-surface-1) px-3 py-2 text-sm"
          />
          <input
            type="text"
            placeholder="Base model"
            value={baseModel}
            onChange={(e) => setBaseModel(e.target.value)}
            className="min-w-[140px] rounded-md border border-(--qs-border-subtle) bg-(--qs-surface-1) px-3 py-2 text-sm"
          />
          <button
            type="button"
            disabled={busyId === "create"}
            onClick={() => void createDraft()}
            className="rounded-md bg-cyan/20 px-4 py-2 text-sm font-medium text-cyan hover:bg-cyan/30 disabled:opacity-50"
          >
            {busyId === "create" ? "Creating…" : "Create draft"}
          </button>
        </div>
        {snapshot.jobs.length === 0 ? (
          <p className="px-4 pb-4 text-sm text-(--qs-text-3)">No jobs yet — export LOC5 JSONL first.</p>
        ) : (
          <ul className="space-y-2 px-4 pb-4">
            {snapshot.jobs.map((job) => (
              <li
                key={job.id}
                className="rounded-md border border-(--qs-border-subtle) bg-(--qs-surface-1)/40 p-3"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{job.adapter_name}</span>
                  <V4Badge tone={job.status === "completed" ? "ok" : "info"}>{job.status}</V4Badge>
                  <span className="font-mono text-xs text-(--qs-text-3)">{job.dataset_row_count} rows</span>
                </div>
                {job.training_plan_summary ? (
                  <p className="mt-1 text-xs text-(--qs-text-3)">{job.training_plan_summary}</p>
                ) : null}
                {job.status === "pending_approval" ? (
                  <button
                    type="button"
                    disabled={busyId === job.id}
                    onClick={() => void approve(job.id)}
                    className="mt-2 rounded-md bg-(--qs-pollen)/20 px-3 py-1.5 text-xs font-medium text-(--qs-pollen) hover:bg-(--qs-pollen)/30 disabled:opacity-50"
                  >
                    {busyId === job.id ? "Approving…" : "Approve & enqueue"}
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </V4Card>
    </div>
  );
}
