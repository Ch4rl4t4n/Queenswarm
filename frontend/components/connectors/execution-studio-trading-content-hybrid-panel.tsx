"use client";

import Link from "next/link";
import { GitBranch } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { cn } from "@/lib/utils";

interface HybridAction {
  id: string;
  label: string;
  detail: string;
  priority: "high" | "medium" | "low";
  href?: string | null;
}

interface TradingContentHybridSnapshot {
  enabled: boolean;
  generated_at: string;
  paper_pnl_usd: number;
  paper_equity_usd: number;
  trade_content_drafts: number;
  publish_pending: number;
  publish_live_posts: number;
  polymarket_prep_pct: number;
  actions: HybridAction[];
}

export interface ExecutionStudioTradingContentHybridPanelProps {
  onError: (message: string | null) => void;
}

function actionTone(priority: HybridAction["priority"]): "ok" | "warn" | "err" | "info" {
  if (priority === "high") return "err";
  if (priority === "medium") return "warn";
  return "info";
}

function ExecutionStudioTradingContentHybridPanelInner({
  onError,
}: ExecutionStudioTradingContentHybridPanelProps) {
  const [snapshot, setSnapshot] = useState<TradingContentHybridSnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    onError(null);
    try {
      const data = await hiveGet<TradingContentHybridSnapshot>("trading-content-hybrid");
      setSnapshot(data);
    } catch (err) {
      if (err instanceof HiveApiError && err.status === 404) {
        setSnapshot(null);
        return;
      }
      onError(err instanceof Error ? err.message : "Hybrid snapshot failed.");
    } finally {
      setLoading(false);
    }
  }, [onError]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!loading && snapshot && !snapshot.enabled) {
    return null;
  }

  return (
    <div id="trading-content-hybrid" className="qs-bubble qs-bubble--tint-amber shrink-0 space-y-3 p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <GitBranch className="size-4 text-pollen" aria-hidden />
          <h3 className="font-heading text-sm font-semibold text-(--qs-text)">Trading + Content Hybrid</h3>
        </div>
        <HiveRefreshButton busy={loading} onClick={() => void load()} />
      </div>

      {loading && !snapshot ? (
        <p className="text-xs text-(--qs-text-3)">Loading dual-lane snapshot…</p>
      ) : snapshot ? (
        <>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <article className="rounded-lg border border-white/10 bg-black/20 p-2">
              <p className="text-[10px] uppercase tracking-wide text-(--qs-text-3)">Paper P&L</p>
              <p className={cn("font-mono text-sm", snapshot.paper_pnl_usd >= 0 ? "text-success" : "text-error")}>
                ${snapshot.paper_pnl_usd.toFixed(2)}
              </p>
            </article>
            <article className="rounded-lg border border-white/10 bg-black/20 p-2">
              <p className="text-[10px] uppercase tracking-wide text-(--qs-text-3)">Equity</p>
              <p className="font-mono text-sm text-cyan">${snapshot.paper_equity_usd.toFixed(2)}</p>
            </article>
            <article className="rounded-lg border border-white/10 bg-black/20 p-2">
              <p className="text-[10px] uppercase tracking-wide text-(--qs-text-3)">Trade→content</p>
              <p className="font-mono text-sm text-pollen">{snapshot.trade_content_drafts}</p>
            </article>
            <article className="rounded-lg border border-white/10 bg-black/20 p-2">
              <p className="text-[10px] uppercase tracking-wide text-(--qs-text-3)">Polymarket prep</p>
              <p className="font-mono text-sm text-(--qs-text)">{snapshot.polymarket_prep_pct}%</p>
            </article>
          </div>

          {snapshot.actions.length > 0 ? (
            <ul className="space-y-2">
              {snapshot.actions.map((action) => (
                <li
                  key={action.id}
                  className="flex flex-wrap items-start justify-between gap-2 rounded-lg border border-white/10 bg-black/20 p-2"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <V4Badge tone={actionTone(action.priority)}>{action.priority}</V4Badge>
                      <span className="text-sm font-medium text-(--qs-text)">{action.label}</span>
                    </div>
                    <p className="mt-1 text-xs text-(--qs-text-3)">{action.detail}</p>
                  </div>
                  {action.href ? (
                    <Link href={action.href} className="text-xs text-cyan hover:underline">
                      Open lane
                    </Link>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-(--qs-text-3)">Both lanes healthy — no urgent hybrid actions.</p>
          )}
        </>
      ) : null}
    </div>
  );
}

export const ExecutionStudioTradingContentHybridPanel = memo(ExecutionStudioTradingContentHybridPanelInner);
