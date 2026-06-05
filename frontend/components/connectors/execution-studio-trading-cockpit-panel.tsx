"use client";

import Link from "next/link";
import { ExternalLink, Loader2, TrendingUp, Wallet } from "lucide-react";
import { memo, useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hiveGet, hivePatchJson } from "@/lib/api";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";

type ExecutionFlow = "simulate_first" | "manual_approve" | "trusted_auto";

interface TradingCockpitSnapshot {
  enabled: boolean;
  generated_at: string;
  config: {
    default_mode: "real";
    venue: "polymarket";
    behavior_principles: string;
    execution_flow: ExecutionFlow;
    trusted_auto_min_simulates: number;
    risk: {
      max_order_usd: number;
      max_daily_loss_usd: number;
      max_risk_pct_per_trade: number;
      confidence_threshold: number;
    };
    notifications: {
      telegram_on_fill: boolean;
      telegram_on_daily_report: boolean;
    };
  };
  venues: Array<{ id: string; label: string; mode: string; description: string }>;
  funding: {
    mode: string;
    venue: string;
    external_url?: string | null;
    connector_ready?: boolean;
    live_trading_enabled?: boolean;
    status?: string;
    message?: string;
  };
  project: { id: string; slug: string; display_name: string; is_active: boolean } | null;
  performance: {
    mode?: string;
    venue?: string;
    is_halted?: boolean;
    halt_reason?: string | null;
  };
  recent_runs: Array<{ id: string; action: string; ok: boolean; created_at: string }>;
  prediction_markets: {
    live_trading_enabled?: boolean;
    connectors_active?: Record<string, boolean>;
    polymarket_readiness?: {
      progress_pct: number;
      ready: boolean;
      steps: Array<{ id: string; label: string; done: boolean; detail: string }>;
    };
  };
  flags: {
    prediction_markets_enabled: boolean;
    live_trading_enabled: boolean;
  };
  links: Record<string, string>;
}

export interface ExecutionStudioTradingCockpitPanelProps {
  onError: (message: string | null) => void;
}

function ExecutionStudioTradingCockpitPanelInner({ onError }: ExecutionStudioTradingCockpitPanelProps) {
  const [snapshot, setSnapshot] = useState<TradingCockpitSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [principles, setPrinciples] = useState("");
  const [flow, setFlow] = useState<ExecutionFlow>("manual_approve");
  const [maxOrder, setMaxOrder] = useState("100");
  const [maxDailyLoss, setMaxDailyLoss] = useState("250");
  const [maxRiskPct, setMaxRiskPct] = useState("2");
  const [confidence, setConfidence] = useState("0.75");

  const load = useCallback(async () => {
    setLoading(true);
    onError(null);
    try {
      const data = await hiveGet<TradingCockpitSnapshot>("trading-cockpit");
      setSnapshot(data);
      const cfg = data.config;
      setPrinciples(cfg.behavior_principles ?? "");
      setFlow(cfg.execution_flow ?? "manual_approve");
      setMaxOrder(String(cfg.risk?.max_order_usd ?? 100));
      setMaxDailyLoss(String(cfg.risk?.max_daily_loss_usd ?? 250));
      setMaxRiskPct(String(cfg.risk?.max_risk_pct_per_trade ?? 2));
      setConfidence(String(cfg.risk?.confidence_threshold ?? 0.75));
    } catch (exc) {
      onError(exc instanceof HiveApiError ? exc.message : "Failed to load Trading Cockpit.");
    } finally {
      setLoading(false);
    }
  }, [onError]);

  useEffect(() => {
    void load();
  }, [load]);

  const saveConfig = useCallback(async () => {
    setSaving(true);
    onError(null);
    try {
      await hivePatchJson("trading-cockpit/config", {
        behavior_principles: principles,
        execution_flow: flow,
        risk: {
          max_order_usd: Number(maxOrder) || 100,
          max_daily_loss_usd: Number(maxDailyLoss) || 250,
          max_risk_pct_per_trade: Number(maxRiskPct) || 2,
          confidence_threshold: Number(confidence) || 0.75,
        },
      });
      toast.success("Polymarket agent config saved.");
      await load();
    } catch (exc) {
      onError(exc instanceof HiveApiError ? exc.message : "Failed to save config.");
    } finally {
      setSaving(false);
    }
  }, [confidence, flow, load, maxDailyLoss, maxOrder, maxRiskPct, onError, principles]);

  const flowHint = useMemo(() => {
    if (flow === "manual_approve") return "Every live order needs explicit operator approval.";
    if (flow === "trusted_auto") return `Auto-live after ${snapshot?.config.trusted_auto_min_simulates ?? 5} verified evaluations.`;
    return "Evaluate markets first — live only via separate executor bot.";
  }, [flow, snapshot?.config.trusted_auto_min_simulates]);

  if (loading && !snapshot) {
    return <div className="qs-bubble shrink-0 min-h-[12rem] animate-pulse bg-white/5 p-4" aria-hidden />;
  }

  if (!snapshot?.enabled) {
    return null;
  }

  const funding = snapshot.funding;
  const readiness = snapshot.prediction_markets.polymarket_readiness;

  return (
    <V4Card id="trading-cockpit" className="shrink-0">
      <V4CardHeader
        as="h3"
        title="Polymarket Trading Cockpit"
        description="Real USDC on Polygon — evaluator swarm + live executor bots. No paper simulation."
        actions={<HiveRefreshButton busy={loading} onClick={() => void load()} />}
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-2">
        <Link href={snapshot.links.evaluator_swarm ?? "/swarms/new?template=polymarket-prediction-evaluator"} className="qs-btn qs-btn--ghost qs-btn--sm justify-start">
          Spawn prediction evaluator swarm
        </Link>
        <Link href={snapshot.links.live_swarm ?? "/swarms/new?template=polymarket-trading"} className="qs-btn qs-btn--ghost qs-btn--sm justify-start">
          Spawn live executor swarm
        </Link>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <article className="qs-bubble-inner space-y-3 p-4">
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">
            <Wallet className="h-3.5 w-3.5" aria-hidden />
            Live lane status
          </p>
          <V4Badge tone={funding?.connector_ready ? "ok" : "warn"}>{funding?.status ?? "polymarket"}</V4Badge>
          <p className="text-xs text-(--qs-text-2)">{funding?.message}</p>
          {funding?.external_url ? (
            <a
              href={funding.external_url}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-1 text-xs text-cyan hover:text-pollen"
            >
              Fund on Polymarket <ExternalLink className="h-3 w-3" aria-hidden />
            </a>
          ) : null}
          {!snapshot.flags.live_trading_enabled ? (
            <p className="text-[11px] text-(--qs-magenta)">
              Live flag off — enable PREDICTION_MARKETS_LIVE_TRADING_ENABLED after CLOB vault + review.
            </p>
          ) : null}
          {readiness ? (
            <div className="mt-2 space-y-1">
              <p className="text-[10px] font-semibold uppercase text-pollen">
                Polymarket prep {readiness.progress_pct}%
              </p>
              <ul className="space-y-1">
                {readiness.steps.map((step) => (
                  <li key={step.id} className="text-[11px] text-(--qs-text-3)">
                    {step.done ? "✓" : "○"} {step.label}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </article>

        <article className="qs-bubble-inner space-y-3 p-4">
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">
            <TrendingUp className="h-3.5 w-3.5" aria-hidden />
            Execution policy
          </p>
          <label className="block text-xs text-(--qs-text-3)">
            Flow
            <select className="qs-input mt-1 w-full" value={flow} onChange={(e) => setFlow(e.target.value as ExecutionFlow)}>
              <option value="manual_approve">Manual approve each live order</option>
              <option value="simulate_first">Evaluate first, then manual live</option>
              <option value="trusted_auto">Trusted auto (after N evaluations)</option>
            </select>
          </label>
          <p className="text-[11px] text-cyan">{flowHint}</p>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-xs text-(--qs-text-3)">
              Max order USD
              <input className="qs-input mt-1 w-full" value={maxOrder} onChange={(e) => setMaxOrder(e.target.value)} />
            </label>
            <label className="text-xs text-(--qs-text-3)">
              Max daily loss USD
              <input className="qs-input mt-1 w-full" value={maxDailyLoss} onChange={(e) => setMaxDailyLoss(e.target.value)} />
            </label>
          </div>
        </article>
      </div>

      <label className="mt-4 block space-y-2">
        <span className="text-xs font-semibold text-(--qs-text-3)">Agent trading principles</span>
        <textarea
          className="qs-input min-h-[100px] w-full font-mono text-xs"
          value={principles}
          onChange={(e) => setPrinciples(e.target.value)}
          placeholder="Risk rules, market filters, when to enter/exit on Polymarket…"
        />
      </label>

      <button type="button" className="qs-btn qs-btn--primary qs-btn--sm mt-3" disabled={saving} onClick={() => void saveConfig()}>
        {saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
        Save agent config
      </button>

      {(snapshot.recent_runs?.length ?? 0) > 0 ? (
        <div className="mt-4">
          <p className="mb-2 text-xs font-semibold uppercase text-(--qs-text-3)">Recent bot runs</p>
          <ul className="max-h-32 space-y-1 overflow-y-auto text-[11px]">
            {snapshot.recent_runs.map((run) => (
              <li key={run.id} className="rounded-lg bg-white/5 px-3 py-2 font-mono">
                {run.action} · {run.ok ? "ok" : "fail"}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2 border-t border-(--qs-border)/40 pt-4">
        <Link href={snapshot.links.external_projects ?? "/external-projects"} className="qs-btn qs-btn--ghost qs-btn--sm">
          External project API
        </Link>
        <Link href={snapshot.links.connectors ?? "/integrations?tab=hub"} className="qs-btn qs-btn--ghost qs-btn--sm">
          Connector hub
        </Link>
      </div>
    </V4Card>
  );
}

export const ExecutionStudioTradingCockpitPanel = memo(ExecutionStudioTradingCockpitPanelInner);
