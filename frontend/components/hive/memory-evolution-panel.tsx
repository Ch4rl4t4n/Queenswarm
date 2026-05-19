"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, X } from "lucide-react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { cn } from "@/lib/utils";

interface MemoryEvolutionProposal {
  id: string;
  proposal_kind: string;
  title: string;
  summary: string;
  payload: Record<string, unknown>;
  status: string;
  importance_score: number;
  requires_manual_approval: boolean;
  created_at: string;
}

/** Pending memory evolution proposals — approve / reject via hive-mind API. */
export function MemoryEvolutionPanel() {
  const [rows, setRows] = useState<MemoryEvolutionProposal[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const payload = await hiveGet<MemoryEvolutionProposal[]>(
        "hive-mind/memory-evolution/proposals?status_filter=pending&limit=20",
      );
      setRows(payload);
      setErr(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Proposals unavailable";
      setErr(msg);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function act(id: string, action: "approve" | "reject") {
    setBusy(id);
    try {
      await hivePostJson(`hive-mind/memory-evolution/proposals/${encodeURIComponent(id)}/${action}`, {});
      toast.success(action === "approve" ? "Proposal approved" : "Proposal rejected");
      await reload();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  const pending = rows.filter((row) => row.status === "pending");

  return (
    <V4Card>
      <V4CardHeader
        title="Memory evolution proposals"
        description="Suggested graph edits from reflection cycles — approve to commit, reject to log."
        actions={<V4Badge tone="purple">{pending.length} pending</V4Badge>}
      />
      {err ? <p className="mb-3 text-sm text-(--qs-red)">{err}</p> : null}
      <div className="flex flex-col gap-3">
        {!pending.length ? (
          <p className="text-sm text-(--qs-text-3)">No pending proposals — reflection cycles will surface edits here.</p>
        ) : (
          pending.map((row) => (
            <div key={row.id} className="v4-spawn-rule">
              <div className="min-w-0 flex-1">
                <div className="text-sm text-(--qs-text)">{row.title || row.summary}</div>
                <div className="mt-1 text-xs text-(--qs-text-3)">
                  {row.summary !== row.title ? row.summary : null}
                  {row.summary !== row.title ? " · " : ""}
                  confidence {row.importance_score.toFixed(2)} · {row.proposal_kind}
                </div>
              </div>
              <div className="flex shrink-0 gap-2">
                <button
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
                  disabled={busy === row.id}
                  onClick={() => void act(row.id, "reject")}
                >
                  <X className="h-3.5 w-3.5" aria-hidden />
                  Reject
                </button>
                <button
                  type="button"
                  className={cn("qs-btn qs-btn--primary qs-btn--sm gap-1.5")}
                  disabled={busy === row.id}
                  onClick={() => void act(row.id, "approve")}
                >
                  <Check className="h-3.5 w-3.5" aria-hidden />
                  Approve
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </V4Card>
  );
}
