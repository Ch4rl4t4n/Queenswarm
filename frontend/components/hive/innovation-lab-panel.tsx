"use client";

import { AlertTriangle, Lightbulb, Loader2, Sparkles } from "lucide-react";
import Link from "next/link";
import { memo, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import {
  InnovationViabilityBanner,
  type ViabilityPayload,
} from "@/components/hive/innovation-viability-banner";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { MANUAL_HREFS } from "@/lib/manual-routes";

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
  const [viabilityById, setViabilityById] = useState<Record<string, ViabilityPayload>>({});
  const [viabilityLoadingId, setViabilityLoadingId] = useState<string | null>(null);
  const [highRiskAck, setHighRiskAck] = useState<Record<string, boolean>>({});

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

  const loadViability = useCallback(async (id: string, acknowledgeHighRisk: boolean) => {
    setViabilityLoadingId(id);
    try {
      const query = acknowledgeHighRisk ? "?acknowledge_high_risk=true" : "";
      const row = await hiveGet<ViabilityPayload>(
        `operator/innovation-lab/proposals/${id}/viability${query}`,
      );
      setViabilityById((prev) => ({ ...prev, [id]: row }));
      return row;
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Viability check failed");
      return null;
    } finally {
      setViabilityLoadingId(null);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    for (const p of proposals) {
      if (p.status === "pending" || p.status === "approved") {
        void loadViability(p.id, highRiskAck[p.id] ?? false);
      }
    }
  }, [proposals, highRiskAck, loadViability]);

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
    async (id: string, decision: "approved" | "rejected", queueMaintainer = false) => {
      const proposal = proposals.find((p) => p.id === id);
      const needsAck = proposal?.risk_level === "high" && queueMaintainer;
      const ack = highRiskAck[id] ?? false;
      if (needsAck && !ack) {
        toast.error("Acknowledge high risk before queueing Maintainer.");
        return;
      }
      setBusy(id);
      try {
        const result = await hivePostJson<{
          ok?: boolean;
          error?: string;
          viability?: ViabilityPayload;
        }>(`operator/innovation-lab/proposals/${id}/review`, {
          decision,
          queue_maintainer: queueMaintainer && decision === "approved",
          acknowledge_high_risk: ack,
        });
        if (result.error === "viability_blocked") {
          toast.error("Viability gate blocked — fix blockers below.");
          if (result.viability) {
            setViabilityById((prev) => ({ ...prev, [id]: result.viability! }));
          }
          return;
        }
        toast.success(
          queueMaintainer && decision === "approved"
            ? "Approved — Queen Maintainer queued (PR-only)."
            : decision === "approved"
              ? "Approved"
              : "Rejected",
        );
        await load();
        onMutate?.();
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Review failed");
      } finally {
        setBusy(null);
      }
    },
    [highRiskAck, load, onMutate, proposals],
  );

  const implementProposal = useCallback(
    async (id: string) => {
      const proposal = proposals.find((p) => p.id === id);
      const ack = highRiskAck[id] ?? false;
      if (proposal?.risk_level === "high" && !ack) {
        toast.error("Acknowledge high risk before Implement.");
        return;
      }
      setBusy(`impl-${id}`);
      try {
        const query = ack ? "?acknowledge_high_risk=true" : "";
        const result = await hivePostJson<{ ok: boolean; error?: string; viability?: ViabilityPayload }>(
          `operator/innovation-lab/proposals/${id}/implement${query}`,
          {},
        );
        if (result.error === "viability_blocked") {
          toast.error("Viability gate blocked — fix blockers below.");
          if (result.viability) {
            setViabilityById((prev) => ({ ...prev, [id]: result.viability! }));
          }
          return;
        }
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
    [highRiskAck, load, onMutate, proposals],
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
      <p className="mb-3 text-xs text-(--qs-text-3)">
        Safe self-improvement: brainstorm → approve → viability gate → Queen Maintainer PR only.{" "}
        <Link href={MANUAL_HREFS.manualInnovationViability} className="text-cyan underline-offset-2 hover:underline">
          Manual → Viability gate
        </Link>
      </p>
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
          {proposals.map((p) => {
            const viability = viabilityById[p.id] ?? null;
            const isHighRisk = p.risk_level === "high";
            const ack = highRiskAck[p.id] ?? false;
            const canQueue = viability?.ok !== false;

            return (
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
                          onClick={() => void reviewProposal(p.id, "approved", false)}
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          className="qs-btn qs-btn--primary qs-btn--sm gap-1"
                          disabled={busy === p.id || !canQueue}
                          title={canQueue ? "Approve and queue Maintainer in one step" : "Fix viability blockers first"}
                          onClick={() => void reviewProposal(p.id, "approved", true)}
                        >
                          <Sparkles className="size-3.5" aria-hidden />
                          Approve &amp; queue
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
                        disabled={busy === `impl-${p.id}` || !canQueue}
                        onClick={() => void implementProposal(p.id)}
                      >
                        <Sparkles className="size-3.5" /> Implement
                      </button>
                    ) : null}
                  </div>
                </div>

                {isHighRisk && (p.status === "pending" || p.status === "approved") ? (
                  <label className="mt-2 flex cursor-pointer items-start gap-2 text-xs text-pollen">
                    <input
                      type="checkbox"
                      className="mt-0.5"
                      checked={ack}
                      onChange={(e) => {
                        const next = e.target.checked;
                        setHighRiskAck((prev) => ({ ...prev, [p.id]: next }));
                        void loadViability(p.id, next);
                      }}
                    />
                    <span className="flex items-center gap-1">
                      <AlertTriangle className="size-3.5 shrink-0" aria-hidden />I acknowledge high risk — Maintainer
                      still PR-only with pre-tool denylist.
                    </span>
                  </label>
                ) : null}

                <InnovationViabilityBanner
                  viability={viability}
                  loading={viabilityLoadingId === p.id}
                />

                {p.implementation_plan_md ? (
                  <pre className="mt-2 max-h-32 overflow-auto font-mono text-[10px] text-(--qs-text-3)">
                    {p.implementation_plan_md.slice(0, 800)}
                  </pre>
                ) : null}
              </li>
            );
          })}
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
