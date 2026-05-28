"use client";

import { Lightbulb, Loader2, Sparkles } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

export interface InnovationProposal {
  id: string;
  title: string;
  status: string;
  risk_level: string;
  feature_modules: string[];
  implementation_plan_md: string;
}

interface InnovationLabPanelProps {
  /** Called after brainstorm / review / implement so parent can refresh counts. */
  onMutate?: () => void;
}

function InnovationLabPanelInner({ onMutate }: InnovationLabPanelProps) {
  const [proposals, setProposals] = useState<InnovationProposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [brainstorm, setBrainstorm] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const lab = await hiveGet<{ proposals: InnovationProposal[] }>("operator/innovation-lab");
      setProposals(lab.proposals ?? []);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Innovation Lab unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const submitBrainstorm = useCallback(async () => {
    const prompt = brainstorm.trim();
    if (prompt.length < 8) {
      toast.error("Enter at least 8 characters for brainstorm.");
      return;
    }
    setBusy("brainstorm");
    try {
      await hivePostJson("operator/innovation-lab/brainstorm", { prompt, category: "feature" });
      toast.success("Proposal created — review and approve.");
      setBrainstorm("");
      await load();
      onMutate?.();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Brainstorm failed");
    } finally {
      setBusy(null);
    }
  }, [brainstorm, load, onMutate]);

  const reviewProposal = useCallback(
    async (id: string, decision: "approved" | "rejected") => {
      setBusy(id);
      try {
        await hivePostJson(`operator/innovation-lab/proposals/${id}/review`, { decision });
        toast.success(decision === "approved" ? "Approved" : "Rejected");
        await load();
        onMutate?.();
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Review failed");
      } finally {
        setBusy(null);
      }
    },
    [load, onMutate],
  );

  const implementProposal = useCallback(
    async (id: string) => {
      setBusy(`impl-${id}`);
      try {
        const result = await hivePostJson<{ ok: boolean }>(
          `operator/innovation-lab/proposals/${id}/implement`,
          {},
        );
        if (result.ok) {
          toast.success("Queen Maintainer queued — PR-only implementation.");
          await load();
          onMutate?.();
        } else {
          toast.error("Implementation failed — check Maintainer logs.");
        }
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Implement failed");
      } finally {
        setBusy(null);
      }
    },
    [load, onMutate],
  );

  if (loading) {
    return (
      <div className="flex min-h-32 items-center justify-center gap-2 text-sm text-(--qs-muted)">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Loading Innovation Lab…
      </div>
    );
  }

  return (
    <>
      <div className="mb-4 space-y-2">
        <textarea
          value={brainstorm}
          onChange={(e) => setBrainstorm(e.target.value)}
          rows={3}
          placeholder="e.g. Add Telegram inbound for Bee Hotline with trust lanes…"
          className="qs-input w-full text-sm"
        />
        <button
          type="button"
          className="qs-btn qs-btn--primary qs-btn--sm gap-1"
          disabled={busy === "brainstorm"}
          onClick={() => void submitBrainstorm()}
        >
          {busy === "brainstorm" ? <Loader2 className="size-4 animate-spin" /> : <Lightbulb className="size-4" />}
          Brainstorm
        </button>
      </div>
      {proposals.length === 0 ? (
        <p className="text-xs text-(--qs-muted)">No proposals yet.</p>
      ) : (
        <ul className="space-y-3">
          {proposals.map((p) => (
            <li key={p.id} className="rounded-lg border border-(--qs-border) bg-black/20 p-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-(--qs-text)">{p.title}</p>
                  <p className="mt-1 text-xs text-(--qs-muted)">
                    {p.status} · risk {p.risk_level} · {p.feature_modules.join(", ")}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {p.status === "pending" ? (
                    <>
                      <button
                        type="button"
                        className="qs-btn qs-btn--primary qs-btn--sm"
                        disabled={busy === p.id}
                        onClick={() => void reviewProposal(p.id, "approved")}
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        className="qs-btn qs-btn--ghost qs-btn--sm"
                        disabled={busy === p.id}
                        onClick={() => void reviewProposal(p.id, "rejected")}
                      >
                        Reject
                      </button>
                    </>
                  ) : null}
                  {p.status === "approved" ? (
                    <button
                      type="button"
                      className="qs-btn qs-btn--primary qs-btn--sm gap-1"
                      disabled={busy === `impl-${p.id}`}
                      onClick={() => void implementProposal(p.id)}
                    >
                      <Sparkles className="size-3.5" /> Implement
                    </button>
                  ) : null}
                </div>
              </div>
              {p.implementation_plan_md ? (
                <pre className="mt-2 max-h-32 overflow-auto font-mono text-[10px] text-(--qs-text-3)">
                  {p.implementation_plan_md.slice(0, 800)}
                </pre>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

export const InnovationLabPanel = memo(InnovationLabPanelInner);

/** Pending proposals count from a loaded list. */
export function innovationPendingCount(proposals: InnovationProposal[]): number {
  return proposals.filter((p) => p.status === "pending").length;
}
