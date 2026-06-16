"use client";

import { CheckCircle2, Loader2, Moon, XCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

type JournalDraftStatus = "pending" | "approved" | "rejected" | "published";

interface JournalDraft {
  id: string;
  status: JournalDraftStatus;
  symbol: string | null;
  side: string | null;
  thesis: string;
  draft_lesson: string;
  critic_score: number;
  critic_pass: boolean;
  created_at: string;
}

interface JournalGardenerSnapshot {
  enabled: boolean;
  pending_count: number;
  published_count: number;
  rejected_count: number;
  last_run_at: string | null;
  last_run_drafts_created: number;
  items: JournalDraft[];
  operator_hint: string;
}

export function JournalStudioGardenerPanel(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<JournalGardenerSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<JournalGardenerSnapshot>("journal-studio/gardener");
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

  const runSweep = useCallback(async () => {
    setRunning(true);
    try {
      const result = await hivePostJson<{ drafts_created?: number }>("journal-studio/gardener/run", {});
      toast.success(`Gardener sweep done — ${result.drafts_created ?? 0} draft(s) created.`);
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Sweep failed");
    } finally {
      setRunning(false);
    }
  }, [load]);

  const review = useCallback(
    async (draftId: string, decision: "approve" | "reject") => {
      setBusyId(draftId);
      try {
        const result = await hivePostJson<{ status: string; wiki_slug?: string | null }>(
          `journal-studio/gardener/drafts/${encodeURIComponent(draftId)}/review`,
          { decision },
        );
        if (decision === "approve" && result.status === "published") {
          toast.success(result.wiki_slug ? `Published to wiki · ${result.wiki_slug}` : "Draft approved.");
        } else {
          toast.success("Draft rejected.");
        }
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
      <div data-testid="journal-studio-gardener-panel">
        <V4Card className="flex items-center gap-2 p-4 text-sm text-white/60">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading overnight gardener…
        </V4Card>
      </div>
    );
  }

  if (!snapshot?.enabled) {
    return (
      <div data-testid="journal-studio-gardener-panel">
        <V4Card className="p-4 text-sm text-white/60">Journal gardener is disabled.</V4Card>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="journal-studio-gardener-panel">
      <V4Card id="journal-studio-gardener" className="border-fuchsia-500/25">
        <V4CardHeader
          leadingIcon={Moon}
          title="Overnight gardener"
          description="Paper fills → draft lesson → operator approve → wiki sync (06:30 UTC beat)."
          actions={
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="rounded-lg border border-white/15 px-3 py-1.5 text-xs text-white/80 hover:bg-white/5"
                onClick={() => void runSweep()}
                disabled={running}
                data-testid="journal-gardener-run"
              >
                {running ? "Running…" : "Run sweep"}
              </button>
              <HiveRefreshButton onClick={() => void load()} aria-label="Refresh gardener" />
            </div>
          }
        />
        <div className="mt-4 flex flex-wrap gap-2">
          <V4Badge tone="warn">{snapshot.pending_count} pending</V4Badge>
          <V4Badge tone="ok">{snapshot.published_count} published</V4Badge>
          <V4Badge tone="purple">{snapshot.rejected_count} rejected</V4Badge>
          {snapshot.last_run_at ? (
            <V4Badge tone="info">Last run +{snapshot.last_run_drafts_created}</V4Badge>
          ) : null}
        </div>
        <p className="mt-3 text-sm text-white/70">{snapshot.operator_hint}</p>
      </V4Card>

      <V4Card>
        <V4CardHeader leadingIcon={Moon} title="Draft lessons" description="Approve before Obsidian/wiki write." />
        {snapshot.items.filter((row) => row.status === "pending").length === 0 ? (
          <p className="mt-4 text-sm text-white/60">No pending drafts.</p>
        ) : (
          <ul className="mt-4 space-y-3">
            {snapshot.items
              .filter((row) => row.status === "pending")
              .map((draft) => (
                <li
                  key={draft.id}
                  className="rounded-lg border border-white/10 bg-white/[0.02] p-3"
                  data-testid={`journal-draft-row-${draft.id}`}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    {draft.symbol ? <V4Badge tone="info">{draft.symbol}</V4Badge> : null}
                    <V4Badge tone={draft.critic_pass ? "ok" : "warn"}>
                      critic {draft.critic_score.toFixed(1)}/5
                    </V4Badge>
                    <span className="font-medium text-white">{draft.thesis || "Draft lesson"}</span>
                  </div>
                  <p className="mt-2 text-sm text-white/70">{draft.draft_lesson}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="inline-flex items-center gap-1 rounded-lg bg-emerald-500/20 px-3 py-1.5 text-xs text-emerald-200"
                      disabled={busyId === draft.id}
                      onClick={() => void review(draft.id, "approve")}
                      data-testid={`journal-draft-approve-${draft.id}`}
                    >
                      <CheckCircle2 className="size-3.5" aria-hidden />
                      Approve
                    </button>
                    <button
                      type="button"
                      className="inline-flex items-center gap-1 rounded-lg bg-red-500/15 px-3 py-1.5 text-xs text-red-200"
                      disabled={busyId === draft.id}
                      onClick={() => void review(draft.id, "reject")}
                      data-testid={`journal-draft-reject-${draft.id}`}
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
