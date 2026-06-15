"use client";

import Link from "next/link";
import { memo, useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import {
  ApprovalCardDeck,
  type ApprovalDeckItem,
} from "@/components/hive/approval-card-deck";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

interface ApprovalInboxItem {
  id: string;
  kind: string;
  lane: string;
  title: string;
  detail: string;
  created_at: string | null;
  href: string;
  source_id: string;
  reject_supported: boolean;
}

interface ApprovalInboxSnapshot {
  enabled: boolean;
  generated_at: string;
  counts: {
    publish_queue: number;
    agent_suggestions: number;
    lane_digests: number;
    innovation: number;
    gumroad_manual: number;
    goldmine_alerts: number;
    total: number;
  };
  items: ApprovalInboxItem[];
}

function kindBadgeTone(kind: string): "gold" | "purple" | "info" | "warn" | "ok" {
  if (kind === "publish_queue") return "info";
  if (kind === "agent_suggestion") return "purple";
  if (kind === "lane_digest") return "ok";
  if (kind === "goldmine_alert") return "warn";
  if (kind === "gumroad_manual") return "gold";
  return "warn";
}

function BusinessApprovalInboxInner(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<ApprovalInboxSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<ApprovalInboxSnapshot>("operator/approvals");
      setSnapshot(data);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Approval inbox unavailable";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const deckItems: ApprovalDeckItem[] = useMemo(() => {
    if (!snapshot?.items.length) return [];
    return snapshot.items
      .filter((item) => item.kind !== "innovation" && item.kind !== "gumroad_manual")
      .map((item) => ({
        id: item.id,
        title: item.title,
        description: item.detail,
        meta: item.lane,
        badge: item.kind.replace(/_/g, " "),
        badgeTone: kindBadgeTone(item.kind),
      }));
  }, [snapshot?.items]);

  const handleApprove = useCallback(
    async (compositeId: string) => {
      const item = snapshot?.items.find((row) => row.id === compositeId);
      if (!item) return;
      setBusyId(compositeId);
      try {
        if (item.kind === "publish_queue") {
          await hivePostJson(`publish-queue/${encodeURIComponent(item.source_id)}/review`, {
            decision: "approve",
          });
        } else if (item.kind === "agent_suggestion") {
          await hivePostJson(`agents/suggestions/${encodeURIComponent(item.source_id)}/review`, {
            decision: "approve",
          });
        } else if (item.kind === "lane_digest") {
          await hivePostJson(
            `solo-operator/four-lanes/digest-inbox/${encodeURIComponent(item.source_id)}/promote`,
            { approve_first: true },
          );
        } else if (item.kind === "goldmine_alert") {
          await hivePostJson(`foragers/${encodeURIComponent(item.source_id)}/promote-task`, {
            mode: "alert",
            include_skill_bundle: true,
          });
        } else {
          window.open(item.href, item.href.startsWith("http") ? "_blank" : "_self");
          return;
        }
        toast.success("Approved");
        await load();
      } catch (e) {
        const msg = e instanceof HiveApiError ? e.message : "Approval failed";
        toast.error(msg);
      } finally {
        setBusyId(null);
      }
    },
    [load, snapshot?.items],
  );

  const handleReject = useCallback(
    async (compositeId: string) => {
      const item = snapshot?.items.find((row) => row.id === compositeId);
      if (!item?.reject_supported) return;
      setBusyId(compositeId);
      try {
        if (item.kind === "publish_queue") {
          await hivePostJson(`publish-queue/${encodeURIComponent(item.source_id)}/review`, {
            decision: "reject",
          });
        } else if (item.kind === "agent_suggestion") {
          await hivePostJson(`agents/suggestions/${encodeURIComponent(item.source_id)}/review`, {
            decision: "reject",
          });
        }
        toast.success("Rejected");
        await load();
      } catch (e) {
        const msg = e instanceof HiveApiError ? e.message : "Reject failed";
        toast.error(msg);
      } finally {
        setBusyId(null);
      }
    },
    [load, snapshot?.items],
  );

  if (!snapshot?.enabled) {
    return null;
  }

  const manualItems = snapshot.items.filter(
    (item) => item.kind === "innovation" || item.kind === "gumroad_manual",
  );

  return (
    <div id="business-approval-inbox">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-cyan">Approval inbox</p>
          <p className="mt-0.5 text-xs text-(--qs-text-2)">
            Publish · goldmine deltas · suggestions · lane digests
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {snapshot.counts.goldmine_alerts > 0 ? (
            <V4Badge tone="warn">{snapshot.counts.goldmine_alerts} goldmine</V4Badge>
          ) : null}
          <V4Badge tone="info">{snapshot.counts.total} pending</V4Badge>
          <HiveRefreshButton busy={loading} onClick={() => void load()} />
        </div>
      </div>

      {snapshot.counts.goldmine_alerts > 0 ? (
        <div
          data-testid="approval-inbox-goldmine-strip"
          className="mb-3 rounded-lg border border-pollen/30 bg-pollen/5 px-3 py-2 text-xs text-(--qs-text-2)"
        >
          <span className="font-medium text-pollen">DG3 delta alerts</span>
          {" — "}
          {snapshot.counts.goldmine_alerts} forager
          {snapshot.counts.goldmine_alerts === 1 ? "" : "s"} with new signals since last run.
          Approve dispatches to Mission Kanban with skill bundle.
        </div>
      ) : null}

      <ApprovalCardDeck
        items={deckItems}
        busyId={busyId}
        emptyLabel="No actionable approvals — inbox clear."
        emptyHint="Factory uploads and Innovation Lab reviews appear here when pending."
        variant="pollen"
        alwaysShowShell={snapshot.counts.total > 0}
        onApprove={handleApprove}
        onReject={handleReject}
      />

      {manualItems.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {manualItems.map((item) => (
            <li
              key={item.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded border border-(--qs-border) bg-black/20 px-3 py-2 text-xs"
            >
              <div>
                <p className="font-medium text-(--qs-text)">{item.title}</p>
                <p className="text-(--qs-muted)">{item.detail}</p>
              </div>
              {item.href.startsWith("http") ? (
                <a
                  href={item.href}
                  className="qs-btn qs-btn--ghost qs-btn--sm"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Open
                </a>
              ) : (
                <Link href={item.href} className="qs-btn qs-btn--ghost qs-btn--sm">
                  Open
                </Link>
              )}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export const BusinessApprovalInbox = memo(BusinessApprovalInboxInner);
BusinessApprovalInbox.displayName = "BusinessApprovalInbox";
