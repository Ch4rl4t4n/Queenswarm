"use client";

import { CheckCircle2, Loader2, Sprout, XCircle } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

type CompoundDraftStatus = "pending" | "approved" | "rejected";

interface BrainPackGap {
  kind: string;
  title: string;
  question: string;
}

interface WeeklyCompoundDraft {
  id: string;
  status: CompoundDraftStatus;
  week_label: string;
  title: string;
  markdown_preview: string;
  proposal_id: string | null;
  brain_pack_gaps: BrainPackGap[];
  created_at: string;
}

interface WeeklyCompoundGardenerSnapshot {
  enabled: boolean;
  pending_count: number;
  last_run_at: string | null;
  last_run_drafts_created: number;
  items: WeeklyCompoundDraft[];
  brain_pack_gaps: BrainPackGap[];
  operator_hint: string;
}

function WeeklyCompoundGardenerPanelInner(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<WeeklyCompoundGardenerSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<WeeklyCompoundGardenerSnapshot>("operator/weekly-compound-gardener");
      setSnapshot(data);
    } catch {
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const review = useCallback(
    async (draftId: string, decision: "approve" | "reject") => {
      setBusyId(draftId);
      try {
        await hivePostJson(`operator/weekly-compound-gardener/${encodeURIComponent(draftId)}/review`, {
          decision,
        });
        toast.success(decision === "approve" ? "Compound draft approved" : "Compound draft rejected");
        await load();
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Review failed");
      } finally {
        setBusyId(null);
      }
    },
    [load],
  );

  if (loading) {
    return (
      <V4Card data-testid="weekly-compound-gardener-panel" className="flex items-center gap-2 p-4 text-sm text-white/60">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Loading weekly compound gardener…
      </V4Card>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  const pending = snapshot.items.filter((row) => row.status === "pending");

  return (
    <div className="space-y-4" data-testid="weekly-compound-gardener-panel">
      <V4Card id="weekly-compound-gardener" className="border-pollen/25">
        <V4CardHeader
          leadingIcon={Sprout}
          kicker="POS-J1"
          title="Weekly compound gardener"
          description="Ballroom + episodic → memory evolution proposal — approve before Hive Mind apply."
          hint={sectionHintNode("knowledgeWeeklyCompound")}
          actions={<HiveRefreshButton onClick={() => void load()} aria-label="Refresh compound gardener" />}
        />
        <div className="mt-3 flex flex-wrap gap-2 px-4 pb-2">
          <V4Badge tone="warn">{snapshot.pending_count} pending</V4Badge>
          {snapshot.brain_pack_gaps.length > 0 ? (
            <V4Badge tone="info">{snapshot.brain_pack_gaps.length} Brain Pack gap(s)</V4Badge>
          ) : null}
          {snapshot.last_run_at ? (
            <V4Badge tone="purple">Last run +{snapshot.last_run_drafts_created}</V4Badge>
          ) : null}
        </div>
        <p className="px-4 pb-4 text-sm text-white/70">{snapshot.operator_hint}</p>
      </V4Card>

      {snapshot.brain_pack_gaps.length > 0 ? (
        <V4Card>
          <V4CardHeader title="Brain Pack gaps" description="Fill in Knowledge → Brain Pack (POS-J2)." />
          <ul className="space-y-2 px-4 pb-4 text-xs text-(--qs-text-2)">
            {snapshot.brain_pack_gaps.map((gap) => (
              <li key={gap.kind} className="rounded-lg border border-cyan/15 bg-black/20 p-2">
                <span className="font-medium text-(--qs-text)">{gap.title}</span>
                <p className="mt-1 text-(--qs-muted)">{gap.question}</p>
              </li>
            ))}
          </ul>
        </V4Card>
      ) : null}

      <V4Card>
        <V4CardHeader title="Pending compound drafts" description="Links to Memory Evolution proposal on approve." />
        {pending.length === 0 ? (
          <p className="px-4 pb-4 text-sm text-white/60">No pending drafts — next tick Sunday UTC.</p>
        ) : (
          <ul className="space-y-3 px-4 pb-4">
            {pending.map((draft) => (
              <li
                key={draft.id}
                className="rounded-lg border border-white/10 bg-white/[0.02] p-3"
                data-testid={`weekly-compound-draft-${draft.id}`}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-white">{draft.title}</span>
                  {draft.week_label ? <V4Badge tone="info">{draft.week_label}</V4Badge> : null}
                </div>
                <p className="mt-2 whitespace-pre-wrap text-sm text-white/70">{draft.markdown_preview}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 rounded-lg bg-emerald-500/20 px-3 py-1.5 text-xs text-emerald-200"
                    disabled={busyId === draft.id}
                    onClick={() => void review(draft.id, "approve")}
                    data-testid={`weekly-compound-approve-${draft.id}`}
                  >
                    <CheckCircle2 className="size-3.5" aria-hidden />
                    Approve
                  </button>
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 rounded-lg bg-red-500/15 px-3 py-1.5 text-xs text-red-200"
                    disabled={busyId === draft.id}
                    onClick={() => void review(draft.id, "reject")}
                    data-testid={`weekly-compound-reject-${draft.id}`}
                  >
                    <XCircle className="size-3.5" aria-hidden />
                    Reject
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </V4Card>
    </div>
  );
}

export const WeeklyCompoundGardenerPanel = memo(WeeklyCompoundGardenerPanelInner);
WeeklyCompoundGardenerPanel.displayName = "WeeklyCompoundGardenerPanel";
