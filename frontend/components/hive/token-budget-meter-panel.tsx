"use client";

import { Gauge, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { V4Badge, V4Card } from "@/components/ui/v4";
import { hiveGet } from "@/lib/api";
import { cn } from "@/lib/utils";

export type TokenBudgetStatus = "ok" | "warn" | "critical";

export interface TokenBudgetLayerState {
  layer_id: string;
  label: string;
  char_count: number;
  estimated_tokens: number;
  filled: boolean;
}

export interface TokenBudgetMeterState {
  enabled: boolean;
  prompt_prefix_chars: number;
  estimated_tokens: number;
  storage_total_chars: number;
  storage_max_chars: number;
  storage_usage_pct: number;
  recall_mode: string;
  recall_char_budget: number;
  estimated_recall_tokens: number;
  max_prompt_chars: number;
  selective_max_chars: number;
  recall_usage_pct: number;
  combined_estimated_tokens: number;
  status: TokenBudgetStatus;
  operator_hint: string;
  layers: TokenBudgetLayerState[];
}

interface TokenBudgetMeterPanelProps {
  variant?: "full" | "compact";
  className?: string;
  refreshKey?: number | string;
}

function statusTone(status: TokenBudgetStatus): string {
  if (status === "critical") {
    return "border-(--qs-red)/40 bg-(--qs-red)/10 text-(--qs-red)";
  }
  if (status === "warn") {
    return "border-pollen/40 bg-pollen/10 text-pollen";
  }
  return "border-success/35 bg-success/5 text-success";
}

function meterBarTone(status: TokenBudgetStatus): string {
  if (status === "critical") {
    return "bg-(--qs-red)";
  }
  if (status === "warn") {
    return "bg-pollen";
  }
  return "bg-success";
}

/** MEM4 — Brain Pack + HiveMind char/token budget meter. */
export function TokenBudgetMeterPanel({
  variant = "full",
  className,
  refreshKey,
}: TokenBudgetMeterPanelProps): JSX.Element | null {
  const [state, setState] = useState<TokenBudgetMeterState | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await hiveGet<TokenBudgetMeterState>("memory/curated/token-budget-meter");
      setState(data);
    } catch {
      setState(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  if (loading) {
    return (
      <div className={cn("flex items-center gap-2 text-xs text-(--qs-text-3)", className)}>
        <Loader2 className="size-3 animate-spin" aria-hidden />
        Loading token budget…
      </div>
    );
  }

  if (!state?.enabled) {
    return null;
  }

  const brainPct = state.max_prompt_chars
    ? Math.min(100, Math.round((state.prompt_prefix_chars / state.max_prompt_chars) * 100))
    : 0;

  if (variant === "compact") {
    return (
      <div
        className={cn("rounded-lg border px-3 py-2", statusTone(state.status), className)}
        data-testid="token-budget-meter-compact"
      >
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <Gauge className="size-3.5 shrink-0" aria-hidden />
          <span className="font-mono">
            ~{state.estimated_tokens} tok Brain Pack · ~{state.estimated_recall_tokens} tok recall
          </span>
          <V4Badge tone={state.status === "ok" ? "ok" : state.status === "warn" ? "warn" : "err"}>
            {state.status}
          </V4Badge>
        </div>
      </div>
    );
  }

  return (
    <V4Card
      className={cn("border-purple-500/25 p-3", className)}
      id="token-budget-meter"
      data-testid="token-budget-meter-panel"
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Gauge className="size-4 text-purple-300" aria-hidden />
        <span className="text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">Token budget</span>
        <V4Badge tone="purple">MEM4</V4Badge>
        <V4Badge tone={state.status === "ok" ? "ok" : state.status === "warn" ? "warn" : "err"}>
          {state.status}
        </V4Badge>
      </div>

      <p className="mb-3 text-xs text-(--qs-text-3)">{state.operator_hint}</p>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-2 rounded-lg border border-(--qs-border) bg-black/20 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
            <span className="font-semibold text-(--qs-text-2)">Brain Pack injection</span>
            <span className="font-mono text-cyan">
              {state.prompt_prefix_chars} chars · ~{state.estimated_tokens} tok
            </span>
          </div>
          <div
            className="h-2 overflow-hidden rounded-full bg-black/40"
            role="progressbar"
            aria-valuenow={brainPct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Brain Pack vs HiveMind cap reference"
          >
            <div className={cn("h-full transition-all", meterBarTone(state.status))} style={{ width: `${brainPct}%` }} />
          </div>
          <p className="text-[10px] text-(--qs-text-4)">
            vs hive_mind_max_prompt_chars reference ({state.max_prompt_chars})
          </p>
        </div>

        <div className="space-y-2 rounded-lg border border-(--qs-border) bg-black/20 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
            <span className="font-semibold text-(--qs-text-2)">HiveMind recall ({state.recall_mode})</span>
            <span className="font-mono text-cyan">
              {state.recall_char_budget} chars · ~{state.estimated_recall_tokens} tok
            </span>
          </div>
          <div
            className="h-2 overflow-hidden rounded-full bg-black/40"
            role="progressbar"
            aria-valuenow={state.recall_usage_pct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Recall char budget utilization"
          >
            <div className="h-full bg-cyan transition-all" style={{ width: `${state.recall_usage_pct}%` }} />
          </div>
          <p className="text-[10px] text-(--qs-text-4)">
            cap {state.max_prompt_chars} · selective default {state.selective_max_chars}
          </p>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <V4Badge tone="info">storage {state.storage_total_chars}/{state.storage_max_chars}</V4Badge>
        <V4Badge tone="gold">combined ~{state.combined_estimated_tokens} tok</V4Badge>
      </div>

      {state.layers.length > 0 ? (
        <ul className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {state.layers.map((layer) => (
            <li
              key={layer.layer_id}
              className={cn(
                "rounded-md border px-2.5 py-2 text-[11px]",
                layer.filled ? "border-cyan/25 bg-cyan/5" : "border-(--qs-border) bg-black/15 opacity-70",
              )}
            >
              <span className="font-semibold uppercase tracking-wide text-(--qs-text-2)">{layer.label}</span>
              <p className="mt-1 font-mono text-(--qs-text-3)">
                {layer.char_count} chars · ~{layer.estimated_tokens} tok
              </p>
            </li>
          ))}
        </ul>
      ) : null}
    </V4Card>
  );
}
