"use client";

import Link from "next/link";
import { Loader2Icon, TrendingUpIcon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { V4Badge, V4Card, V4CardHeader, V4Stat } from "@/components/ui/v4";
import { COCKPIT_POLL_COLONY_TELEMETRY_MS } from "@/lib/cockpit-poll-profile";
import { HiveApiError, hiveGet } from "@/lib/api";
import type { PaperTradingSummaryPayload } from "@/lib/hive-types";

function fmtUsd(n: number): string {
  const sign = n < 0 ? "-" : "";
  return `${sign}$${Math.abs(n).toFixed(2)}`;
}

/** Queen dashboard widget — paper trading P&L (no live broker). */
export function PaperTradingPanel(): JSX.Element {
  const [summary, setSummary] = useState<PaperTradingSummaryPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const payload = await hiveGet<PaperTradingSummaryPayload>("paper-trading/summary");
      setSummary(payload);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Paper trading unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const id = window.setInterval(() => void load(), COCKPIT_POLL_COLONY_TELEMETRY_MS);
    return () => window.clearInterval(id);
  }, [load]);

  const top = summary?.projects?.[0];

  return (
    <V4Card>
      <V4CardHeader
        title="Paper trading bee"
        description="Simulated fills · guardrails · no live wallet"
        actions={
          <V4Badge tone="info">
            <TrendingUpIcon className="mr-1 inline h-3 w-3" aria-hidden />
            paper
          </V4Badge>
        }
      />

      {loading ? (
        <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading paper P&L…
        </p>
      ) : null}

      {err ? <p className="text-sm text-(--qs-red)">{err}</p> : null}

      {!loading && !err && (summary?.project_count ?? 0) === 0 ? (
        <div className="space-y-2 text-sm text-(--qs-text-3)">
          <p>No paper trading project yet.</p>
          <Link href="/integrations?tab=external" className="text-cyan underline-offset-2 hover:underline">
            Create external project (kind: trading, mode: paper)
          </Link>
        </div>
      ) : null}

      {!loading && !err && summary && (summary.project_count ?? 0) > 0 ? (
        <>
          <div className="v4-stat-grid mt-2">
            <V4Stat
              label="Total P&L"
              value={fmtUsd(summary.total_pnl_usd ?? 0)}
              foot={`${summary.project_count} project(s)`}
              valueVariant={(summary.total_pnl_usd ?? 0) >= 0 ? "gold" : "text"}
            />
            <V4Stat label="Equity" value={fmtUsd(summary.total_equity_usd ?? 0)} foot="Simulated" />
          </div>

          {top ? (
            <div className="mt-4 rounded-xl border border-(--qs-border) bg-black/25 p-3 text-sm">
              <p className="font-medium text-(--qs-text)">{top.display_name}</p>
              <p className="mt-1 text-xs text-(--qs-text-3)">
                {top.total_pnl_pct != null ? `${top.total_pnl_pct.toFixed(2)}%` : "—"} · cash {fmtUsd(top.cash_usd ?? 0)}
                {top.is_halted ? " · halted" : ""}
              </p>
              {(top.recent_fills ?? []).slice(0, 3).map((fill) => (
                <p key={fill.id} className="mt-2 font-mono text-[11px] text-(--qs-text-2)">
                  {fill.side.toUpperCase()} {fill.quantity} {fill.symbol} @ {fmtUsd(fill.fill_price_usd)}
                </p>
              ))}
            </div>
          ) : null}

          <p className="mt-3 text-[10px] text-(--qs-text-3)">{summary.disclaimer}</p>
        </>
      ) : null}
    </V4Card>
  );
}
