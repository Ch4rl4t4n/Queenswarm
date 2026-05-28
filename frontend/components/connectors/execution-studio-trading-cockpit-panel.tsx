"use client";

import Link from "next/link";
import { ExternalLink, Loader2, TrendingUp, Wallet } from "lucide-react";
import { memo, useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { cn } from "@/lib/utils";

type TradingMode = "paper" | "real";
type TradingVenueId = "paper_crypto" | "polymarket";
type ExecutionFlow = "simulate_first" | "manual_approve" | "trusted_auto";

interface TradingVenueRow {
  id: TradingVenueId;
  label: string;
  mode: string;
  description: string;
}

interface TradingCockpitSnapshot {
  enabled: boolean;
  generated_at: string;
  config: {
    default_mode: TradingMode;
    venue: TradingVenueId;
    behavior_principles: string;
    execution_flow: ExecutionFlow;
    trusted_auto_min_simulates: number;
    auto_tick: boolean;
    watchlist: string[];
    risk: {
      max_order_usd: number;
      max_daily_loss_usd: number;
      max_risk_pct_per_trade: number;
      confidence_threshold: number;
      starting_cash_usd?: number;
    };
    notifications: {
      telegram_on_fill: boolean;
      telegram_on_daily_report: boolean;
    };
  };
  venues: TradingVenueRow[];
  funding: {
    mode: string;
    venue: string;
    cash_usd?: number;
    deposit_allowed?: boolean;
    external_url?: string | null;
    connector_ready?: boolean;
    live_trading_enabled?: boolean;
    status?: string;
    message?: string;
  };
  project: {
    id: string;
    slug: string;
    display_name: string;
    is_active: boolean;
  } | null;
  performance: {
    equity_usd?: number;
    total_pnl_usd?: number;
    total_pnl_pct?: number;
    realized_pnl_usd?: number;
    daily_realized_pnl_usd?: number;
    is_halted?: boolean;
    halt_reason?: string | null;
    stats?: { total_fills: number; buy_count: number; sell_count: number };
  };
  positions: Array<{
    symbol: string;
    quantity: number;
    mark_price_usd: number;
    market_value_usd: number;
    unrealized_pnl_usd: number;
  }>;
  recent_fills: Array<{
    id: string;
    symbol: string;
    side: string;
    quantity: number;
    fill_price_usd: number;
    signal_note: string;
    created_at: string;
  }>;
  recent_runs: Array<{
    id: string;
    action: string;
    ok: boolean;
    created_at: string;
  }>;
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
    paper_trading_enabled: boolean;
    prediction_markets_enabled: boolean;
    live_trading_enabled: boolean;
  };
  links: Record<string, string>;
}

export interface ExecutionStudioTradingCockpitPanelProps {
  onError: (message: string | null) => void;
}

function pnlTone(value: number | undefined): "ok" | "err" | "info" {
  if (value === undefined || value === 0) return "info";
  return value > 0 ? "ok" : "err";
}

function ExecutionStudioTradingCockpitPanelInner({ onError }: ExecutionStudioTradingCockpitPanelProps) {
  const [snapshot, setSnapshot] = useState<TradingCockpitSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [depositAmount, setDepositAmount] = useState("1000");
  const [depositBusy, setDepositBusy] = useState(false);
  const [tickBusy, setTickBusy] = useState(false);

  const [principles, setPrinciples] = useState("");
  const [watchlistText, setWatchlistText] = useState("BTC, ETH");
  const [venue, setVenue] = useState<TradingVenueId>("paper_crypto");
  const [mode, setMode] = useState<TradingMode>("paper");
  const [flow, setFlow] = useState<ExecutionFlow>("simulate_first");
  const [maxOrder, setMaxOrder] = useState("2500");
  const [maxDailyLoss, setMaxDailyLoss] = useState("500");
  const [maxRiskPct, setMaxRiskPct] = useState("2");
  const [confidence, setConfidence] = useState("0.8");
  const [autoTick, setAutoTick] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    onError(null);
    try {
      const data = await hiveGet<TradingCockpitSnapshot>("trading-cockpit");
      setSnapshot(data);
      const cfg = data.config;
      setPrinciples(cfg.behavior_principles ?? "");
      setWatchlistText((cfg.watchlist ?? []).join(", "));
      setVenue(cfg.venue ?? "paper_crypto");
      setMode(cfg.default_mode ?? "paper");
      setFlow(cfg.execution_flow ?? "simulate_first");
      setMaxOrder(String(cfg.risk?.max_order_usd ?? 2500));
      setMaxDailyLoss(String(cfg.risk?.max_daily_loss_usd ?? 500));
      setMaxRiskPct(String(cfg.risk?.max_risk_pct_per_trade ?? 2));
      setConfidence(String(cfg.risk?.confidence_threshold ?? 0.8));
      setAutoTick(cfg.auto_tick ?? true);
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
        default_mode: mode,
        venue,
        behavior_principles: principles,
        execution_flow: flow,
        auto_tick: autoTick,
        watchlist: watchlistText
          .split(/[,;\s]+/)
          .map((s) => s.trim().toUpperCase())
          .filter(Boolean)
          .slice(0, 12),
        risk: {
          max_order_usd: Number(maxOrder) || 2500,
          max_daily_loss_usd: Number(maxDailyLoss) || 500,
          max_risk_pct_per_trade: Number(maxRiskPct) || 2,
          confidence_threshold: Number(confidence) || 0.8,
        },
      });
      toast.success("Trading agent config saved.");
      await load();
    } catch (exc) {
      onError(exc instanceof HiveApiError ? exc.message : "Failed to save config.");
    } finally {
      setSaving(false);
    }
  }, [
    autoTick,
    confidence,
    flow,
    load,
    maxDailyLoss,
    maxOrder,
    maxRiskPct,
    mode,
    onError,
    principles,
    venue,
    watchlistText,
  ]);

  const depositPaper = useCallback(async () => {
    const amount = Number(depositAmount);
    if (!Number.isFinite(amount) || amount <= 0) {
      toast.error("Enter a valid deposit amount.");
      return;
    }
    setDepositBusy(true);
    onError(null);
    try {
      const out = await hivePostJson<{ cash_usd: number; deposited_usd: number }>(
        "trading-cockpit/paper/deposit",
        { amount_usd: amount },
      );
      toast.success(`Deposited $${out.deposited_usd} paper USD (balance $${out.cash_usd}).`);
      await load();
    } catch (exc) {
      onError(exc instanceof HiveApiError ? exc.message : "Paper deposit failed.");
    } finally {
      setDepositBusy(false);
    }
  }, [depositAmount, load, onError]);

  const runTick = useCallback(async () => {
    setTickBusy(true);
    onError(null);
    try {
      const out = await hivePostJson<{ status: string; symbol?: string; side?: string }>(
        "trading-cockpit/paper/tick",
        {},
      );
      toast.message(`Paper tick: ${out.status}${out.symbol ? ` · ${out.side} ${out.symbol}` : ""}`);
      await load();
    } catch (exc) {
      onError(exc instanceof HiveApiError ? exc.message : "Paper tick failed.");
    } finally {
      setTickBusy(false);
    }
  }, [load, onError]);

  const onVenueChange = useCallback((next: TradingVenueId) => {
    setVenue(next);
    setMode(next === "paper_crypto" ? "paper" : "real");
  }, []);

  const perf = snapshot?.performance;
  const funding = snapshot?.funding;

  const flowHint = useMemo(() => {
    if (flow === "simulate_first") return "Paper/sim only until you switch mode + enable live flags.";
    if (flow === "manual_approve") return "Every live order needs human_approval_confirmed + ticket.";
    return `Auto-live after ${snapshot?.config.trusted_auto_min_simulates ?? 5} verified simulates.`;
  }, [flow, snapshot?.config.trusted_auto_min_simulates]);

  if (loading && !snapshot) {
    return <div className="qs-bubble shrink-0 min-h-[12rem] animate-pulse bg-white/5 p-4" aria-hidden />;
  }

  if (!snapshot?.enabled) {
    return null;
  }

  return (
    <V4Card id="trading-cockpit" className="shrink-0">
      <V4CardHeader
        as="h3"
        title="Trading Cockpit"
        description="Paper + real prediction markets — capital, venue, agent principles, live P&L."
        actions={
          <HiveRefreshButton busy={loading} onClick={() => void load()} />
        }
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <article className="qs-bubble-inner space-y-3 p-4 lg:col-span-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">Mode & venue</p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className={cn("qs-btn qs-btn--sm", mode === "paper" ? "qs-btn--primary" : "qs-btn--ghost")}
              onClick={() => {
                setMode("paper");
                setVenue("paper_crypto");
              }}
            >
              Paper
            </button>
            <button
              type="button"
              className={cn("qs-btn qs-btn--sm", mode === "real" ? "qs-btn--primary" : "qs-btn--ghost")}
              onClick={() => {
                setMode("real");
                if (venue === "paper_crypto") setVenue("polymarket");
              }}
            >
              Real money
            </button>
          </div>
          <label className="block text-xs text-(--qs-text-3)">
            Where to trade
            <select
              className="qs-input mt-1 w-full"
              value={venue}
              onChange={(e) => onVenueChange(e.target.value as TradingVenueId)}
            >
              {(snapshot.venues ?? []).map((v) => (
                <option key={v.id} value={v.id}>
                  {v.label}
                </option>
              ))}
            </select>
          </label>
          <p className="text-[11px] text-(--qs-text-4)">
            {(snapshot.venues ?? []).find((v) => v.id === venue)?.description}
          </p>
          <label className="block text-xs text-(--qs-text-3)">
            Execution flow
            <select className="qs-input mt-1 w-full" value={flow} onChange={(e) => setFlow(e.target.value as ExecutionFlow)}>
              <option value="simulate_first">Simulate first</option>
              <option value="manual_approve">Manual approve each live order</option>
              <option value="trusted_auto">Trusted auto (after N simulates)</option>
            </select>
          </label>
          <p className="text-[11px] text-cyan">{flowHint}</p>
        </article>

        <article className="qs-bubble-inner space-y-3 p-4 lg:col-span-1">
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">
            <Wallet className="h-3.5 w-3.5" aria-hidden />
            Capital
          </p>
          {funding?.deposit_allowed ? (
            <>
              <p className="font-mono text-lg text-pollen">${funding.cash_usd?.toLocaleString() ?? "0"} paper USD</p>
              <div className="flex flex-wrap gap-2">
                <input
                  type="number"
                  min={1}
                  className="qs-input w-28"
                  value={depositAmount}
                  onChange={(e) => setDepositAmount(e.target.value)}
                  aria-label="Paper deposit amount USD"
                />
                <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" disabled={depositBusy} onClick={() => void depositPaper()}>
                  {depositBusy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
                  Deposit paper
                </button>
              </div>
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" disabled={tickBusy} onClick={() => void runTick()}>
                {tickBusy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
                Run paper tick now
              </button>
            </>
          ) : (
            <>
              <V4Badge tone={funding?.connector_ready ? "ok" : "warn"}>{funding?.status ?? "real"}</V4Badge>
              <p className="text-xs text-(--qs-text-2)">{funding?.message}</p>
              {funding?.external_url ? (
                <a
                  href={funding.external_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="inline-flex items-center gap-1 text-xs text-cyan hover:text-pollen"
                >
                  Fund on {funding.venue} <ExternalLink className="h-3 w-3" aria-hidden />
                </a>
              ) : null}
              {!snapshot.flags.live_trading_enabled ? (
                <p className="text-[11px] text-(--qs-magenta)">
                  Live flag off — enable PREDICTION_MARKETS_LIVE_TRADING_ENABLED after connector vault + review.
                </p>
              ) : null}
              {venue === "polymarket" && snapshot.prediction_markets.polymarket_readiness ? (
                <div className="mt-2 space-y-1">
                  <p className="text-[10px] font-semibold uppercase text-pollen">
                    Polymarket prep {snapshot.prediction_markets.polymarket_readiness.progress_pct}%
                  </p>
                  <ul className="space-y-1">
                    {snapshot.prediction_markets.polymarket_readiness.steps.map((step) => (
                      <li key={step.id} className="text-[11px] text-(--qs-text-3)">
                        {step.done ? "✓" : "○"} {step.label}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </>
          )}
        </article>

        <article className="qs-bubble-inner space-y-2 p-4 lg:col-span-1">
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">
            <TrendingUp className="h-3.5 w-3.5" aria-hidden />
            Live performance
          </p>
          <p className="font-mono text-2xl text-(--qs-text)">${perf?.equity_usd?.toLocaleString() ?? "—"}</p>
          <div className="flex flex-wrap gap-2 text-xs">
            <V4Badge tone={pnlTone(perf?.total_pnl_usd)}>P&L ${perf?.total_pnl_usd ?? 0}</V4Badge>
            <V4Badge tone={pnlTone(perf?.total_pnl_pct)}>{perf?.total_pnl_pct ?? 0}%</V4Badge>
            <span className="font-mono text-(--qs-text-4)">{perf?.stats?.total_fills ?? 0} fills</span>
          </div>
          {perf?.is_halted ? (
            <p className="text-xs text-(--qs-red)">Halted: {perf.halt_reason}</p>
          ) : null}
        </article>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <label className="block space-y-2">
          <span className="text-xs font-semibold text-(--qs-text-3)">Agent trading principles</span>
          <textarea
            className="qs-input min-h-[120px] w-full font-mono text-xs"
            value={principles}
            onChange={(e) => setPrinciples(e.target.value)}
            placeholder="Risk rules, market filters, when to enter/exit…"
          />
        </label>
        <div className="space-y-3">
          <label className="block text-xs text-(--qs-text-3)">
            Watchlist (paper crypto)
            <input className="qs-input mt-1 w-full" value={watchlistText} onChange={(e) => setWatchlistText(e.target.value)} />
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-xs text-(--qs-text-3)">
              Max order USD
              <input className="qs-input mt-1 w-full" value={maxOrder} onChange={(e) => setMaxOrder(e.target.value)} />
            </label>
            <label className="text-xs text-(--qs-text-3)">
              Max daily loss USD
              <input className="qs-input mt-1 w-full" value={maxDailyLoss} onChange={(e) => setMaxDailyLoss(e.target.value)} />
            </label>
            <label className="text-xs text-(--qs-text-3)">
              Risk % / trade
              <input className="qs-input mt-1 w-full" value={maxRiskPct} onChange={(e) => setMaxRiskPct(e.target.value)} />
            </label>
            <label className="text-xs text-(--qs-text-3)">
              Min confidence
              <input className="qs-input mt-1 w-full" value={confidence} onChange={(e) => setConfidence(e.target.value)} />
            </label>
          </div>
          <label className="flex items-center gap-2 text-xs text-(--qs-text-2)">
            <input type="checkbox" checked={autoTick} onChange={(e) => setAutoTick(e.target.checked)} className="accent-pollen" />
            Auto paper tick (Celery beat)
          </label>
          <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" disabled={saving} onClick={() => void saveConfig()}>
            {saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
            Save agent config
          </button>
        </div>
      </div>

      {(snapshot.positions?.length ?? 0) > 0 ? (
        <div className="mt-4">
          <p className="mb-2 text-xs font-semibold uppercase text-(--qs-text-3)">Open positions</p>
          <ul className="space-y-1 text-xs">
            {snapshot.positions.map((p) => (
              <li key={p.symbol} className="flex flex-wrap justify-between gap-2 rounded-lg bg-white/5 px-3 py-2 font-mono">
                <span>{p.symbol}</span>
                <span>{p.quantity}</span>
                <span className={p.unrealized_pnl_usd >= 0 ? "text-(--qs-green)" : "text-(--qs-red)"}>
                  uP&L ${p.unrealized_pnl_usd}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {(snapshot.recent_fills?.length ?? 0) > 0 ? (
        <div className="mt-4">
          <p className="mb-2 text-xs font-semibold uppercase text-(--qs-text-3)">Recent fills</p>
          <ul className="max-h-40 space-y-1 overflow-y-auto text-[11px]">
            {snapshot.recent_fills.map((f) => (
              <li key={f.id} className="rounded-lg bg-white/5 px-3 py-2">
                <span className="font-mono uppercase text-cyan">{f.side}</span> {f.quantity} {f.symbol} @ ${f.fill_price_usd}
                <span className="ml-2 text-(--qs-text-4)">{f.signal_note}</span>
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
        {snapshot.project ? (
          <span className="self-center font-mono text-[10px] text-(--qs-text-4)">{snapshot.project.slug}</span>
        ) : null}
      </div>
    </V4Card>
  );
}

export const ExecutionStudioTradingCockpitPanel = memo(ExecutionStudioTradingCockpitPanelInner);
