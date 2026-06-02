"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { ArrowRight, Loader2, Sunrise } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";

interface OperatorLoopAction {
  id: string;
  label: string;
  detail: string;
  priority: "high" | "medium" | "low";
  href: string | null;
}

interface OperatorLoopSnapshot {
  enabled: boolean;
  generated_at: string;
  phase: string;
  overnight: {
    available: boolean;
    items_ingested?: number;
    stalled_signals?: number;
    pollen_earned?: number;
    briefing_preview?: string;
    reason?: string;
  };
  morning_brief: { markdown?: string; tech_health_score?: number };
  publish_pipeline: {
    pending_publish_count?: number;
    approved_publish_count?: number;
  };
  publish_onboarding: { progress_pct?: number };
  trading: {
    performance?: { total_pnl_usd?: number; is_halted?: boolean; halt_reason?: string };
    config?: { default_mode?: string };
  };
  actions: OperatorLoopAction[];
  links: Record<string, string>;
}

function actionTone(priority: OperatorLoopAction["priority"]): "ok" | "warn" | "err" | "info" {
  if (priority === "high") return "err";
  if (priority === "medium") return "warn";
  return "info";
}

function OperatorLoopPanelInner() {
  const [snapshot, setSnapshot] = useState<OperatorLoopSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<OperatorLoopSnapshot>("solo-operator/operator-loop");
      setSnapshot(data);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Operator Loop unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading && !snapshot) {
    return (
      <p className="flex items-center gap-2 text-sm text-(--qs-muted)">
        <Loader2 className="size-4 animate-spin" aria-hidden /> Loading Operator Loop…
      </p>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  const pending = snapshot.publish_pipeline.pending_publish_count ?? 0;
  const onboardPct = snapshot.publish_onboarding.progress_pct ?? 0;
  const pnl = snapshot.trading.performance?.total_pnl_usd ?? 0;
  const overnight = snapshot.overnight;

  return (
    <V4Card id="operator-loop">
      <V4CardHeader
        kicker="Daily command center"
        title="Operator Loop"
        description="Overnight dump, morning brief, publish queue, and paper trading — one snapshot."
        actions={<HiveRefreshButton busy={loading} onClick={() => void load()} />}
      />
      {err ? <p className="mb-3 text-sm text-(--qs-red)">{err}</p> : null}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <V4Badge tone="info">
          <Sunrise className="mr-1 inline size-3" aria-hidden />
          {snapshot.phase}
        </V4Badge>
        <V4Badge tone={pending > 0 ? "warn" : "ok"}>{pending} publish pending</V4Badge>
        <V4Badge tone={onboardPct >= 100 ? "ok" : "warn"}>Onboarding {onboardPct}%</V4Badge>
        <V4Badge tone={pnl >= 0 ? "ok" : "err"}>Paper P&L ${pnl.toFixed(2)}</V4Badge>
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-(--qs-border) bg-black/20 p-3 text-sm">
          <p className="font-semibold text-(--qs-text)">Overnight Dump & Sleep</p>
          {overnight.available ? (
            <>
              <p className="mt-1 text-xs text-(--qs-muted)">
                {overnight.items_ingested ?? 0} items · {overnight.stalled_signals ?? 0} stalled ·{" "}
                {overnight.pollen_earned?.toFixed(1) ?? 0} pollen
              </p>
              {overnight.briefing_preview ? (
                <pre className="mt-2 max-h-24 overflow-auto font-mono text-[10px] text-(--qs-text-3)">
                  {overnight.briefing_preview.slice(0, 400)}
                </pre>
              ) : null}
            </>
          ) : (
            <p className="mt-1 text-xs text-(--qs-muted)">
              No overnight batch —{" "}
              <Link href="/ballroom" className="text-cyan underline">
                upload in Ballroom
              </Link>
            </p>
          )}
        </div>
        <div className="rounded-lg border border-(--qs-border) bg-black/20 p-3 text-sm">
          <p className="font-semibold text-(--qs-text)">Trading Cockpit</p>
          {snapshot.trading.performance?.is_halted ? (
            <p className="mt-1 text-xs text-(--qs-red)">
              Halted: {snapshot.trading.performance.halt_reason ?? "daily stop-loss"}
            </p>
          ) : (
            <p className="mt-1 text-xs text-(--qs-muted)">
              Mode: {snapshot.trading.config?.default_mode ?? "paper"} · equity tracked in Execution Studio
            </p>
          )}
          <Link
            href={snapshot.links.trading_cockpit ?? "/integrations?tab=studio#trading-cockpit"}
            className="mt-2 inline-flex items-center gap-1 text-xs text-cyan hover:text-pollen"
          >
            Open cockpit <ArrowRight className="size-3" aria-hidden />
          </Link>
        </div>
      </div>

      {snapshot.actions.length > 0 ? (
        <ul className="space-y-2">
          {snapshot.actions.map((action) => (
            <li
              key={action.id}
              className="flex flex-wrap items-start justify-between gap-2 rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-(--qs-text)">{action.label}</span>
                  <V4Badge tone={actionTone(action.priority)}>{action.priority}</V4Badge>
                </div>
                <p className="mt-0.5 text-xs text-(--qs-muted)">{action.detail}</p>
              </div>
              {action.href ? (
                <Link href={action.href} className="qs-btn qs-btn--ghost qs-btn--sm shrink-0">
                  Go
                </Link>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-(--qs-green)">All clear — no urgent actions.</p>
      )}

      {snapshot.morning_brief.markdown ? (
        <pre className="mt-4 max-h-40 overflow-auto rounded-lg border border-(--qs-border) bg-black/30 p-3 font-mono text-xs leading-relaxed text-(--qs-text)">
          {snapshot.morning_brief.markdown.slice(0, 1200)}
        </pre>
      ) : null}
    </V4Card>
  );
}

export const OperatorLoopPanel = memo(OperatorLoopPanelInner);
OperatorLoopPanel.displayName = "OperatorLoopPanel";

const LazyOperatorLoopPanel = dynamic(() => Promise.resolve({ default: OperatorLoopPanel }), {
  ssr: false,
  loading: () => (
    <p className="flex items-center gap-2 text-sm text-(--qs-muted)">
      <Loader2 className="size-4 animate-spin" aria-hidden /> Loading Operator Loop…
    </p>
  ),
});

export { LazyOperatorLoopPanel };
