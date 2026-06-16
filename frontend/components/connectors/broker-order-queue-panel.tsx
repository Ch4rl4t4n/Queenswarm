"use client";

import { CheckCircle2, Loader2, ShieldAlert, XCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

type BrokerOrderStatus = "pending" | "approved" | "rejected" | "executed" | "failed";

interface BrokerOrderItem {
  id: string;
  status: BrokerOrderStatus;
  venue: string;
  title: string;
  detail: string;
  notional_usd: number;
  created_at: string;
  execution_status: string | null;
  execution_detail: string | null;
}

interface BrokerOrderQueueSnapshot {
  enabled: boolean;
  pending_count: number;
  executed_count: number;
  rejected_count: number;
  items: BrokerOrderItem[];
  operator_hint: string;
}

function statusBadge(status: BrokerOrderStatus): { label: string; tone: "ok" | "warn" | "err" | "info" } {
  if (status === "pending") return { label: "Pending HITL", tone: "warn" };
  if (status === "executed") return { label: "Executed", tone: "ok" };
  if (status === "rejected") return { label: "Rejected", tone: "err" };
  if (status === "failed") return { label: "Failed", tone: "err" };
  return { label: status, tone: "info" };
}

export function BrokerOrderQueuePanel(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<BrokerOrderQueueSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<BrokerOrderQueueSnapshot>("trading-cockpit/order-queue");
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
    async (orderId: string, decision: "approve" | "reject") => {
      setBusyId(orderId);
      try {
        const result = await hivePostJson<{ status: string; execution_detail?: string }>(
          `trading-cockpit/order-queue/${encodeURIComponent(orderId)}/review`,
          { decision },
        );
        if (decision === "approve" && result.status === "executed") {
          toast.success("Order executed after approval.");
        } else if (decision === "approve" && result.status === "failed") {
          toast.error(result.execution_detail || "Execution failed after approval.");
        } else if (decision === "reject") {
          toast.success("Order rejected.");
        } else {
          toast.success("Review saved.");
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
      <div data-testid="broker-order-queue-panel">
        <V4Card className="flex items-center gap-2 p-4 text-sm text-white/60">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading broker order queue…
        </V4Card>
      </div>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  return (
    <div id="broker-order-queue" data-testid="broker-order-queue-panel">
      <V4Card className="space-y-4 p-4">
        <V4CardHeader
          kicker="Track P · RA5"
          title="HITL order queue"
          description="Agent proposes → you approve → MCP executes with guardrails + audit."
          leadingIcon={ShieldAlert}
          actions={<HiveRefreshButton busy={loading} onClick={() => void load()} />}
        />

        <p className="text-sm text-white/70">{snapshot.operator_hint}</p>

        <div className="flex flex-wrap gap-2">
          <V4Badge tone="warn">{snapshot.pending_count} pending</V4Badge>
          <V4Badge tone="ok">{snapshot.executed_count} executed</V4Badge>
          <V4Badge tone="err">{snapshot.rejected_count} rejected</V4Badge>
        </div>

        {snapshot.items.length === 0 ? (
          <p className="text-sm text-white/50">No broker orders in queue.</p>
        ) : (
          <ul className="space-y-3">
            {snapshot.items.map((item) => {
              const badge = statusBadge(item.status);
              return (
                <li
                  key={item.id}
                  className="rounded-lg border border-white/10 bg-black/20 p-3 text-sm"
                  data-testid={`broker-order-row-${item.id}`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="font-medium text-white">{item.title}</p>
                      <p className="text-xs text-white/50">
                        {item.venue} · ${item.notional_usd.toFixed(2)} · {item.id.slice(0, 8)}
                      </p>
                      {item.detail ? <p className="mt-1 text-white/60">{item.detail}</p> : null}
                      {item.execution_detail ? (
                        <p className="mt-1 font-mono text-xs text-(--qs-magenta)">{item.execution_detail}</p>
                      ) : null}
                    </div>
                    <V4Badge tone={badge.tone}>{badge.label}</V4Badge>
                  </div>
                  {item.status === "pending" ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="qs-btn qs-btn--primary qs-btn--sm"
                        disabled={busyId === item.id}
                        onClick={() => void review(item.id, "approve")}
                      >
                        {busyId === item.id ? (
                          <Loader2 className="size-4 animate-spin" />
                        ) : (
                          <CheckCircle2 className="size-4" />
                        )}
                        Approve & execute
                      </button>
                      <button
                        type="button"
                        className="qs-btn qs-btn--ghost qs-btn--sm"
                        disabled={busyId === item.id}
                        onClick={() => void review(item.id, "reject")}
                      >
                        <XCircle className="size-4" />
                        Reject
                      </button>
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </V4Card>
    </div>
  );
}
