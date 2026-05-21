"use client";

import { Loader2Icon, PiggyBank } from "lucide-react";
import { useCallback, useState } from "react";

import { usePlatform } from "@/components/hive/platform-context";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { COCKPIT_POLL_COLONY_TELEMETRY_MS } from "@/lib/cockpit-poll-profile";
import { HiveApiError, hiveGet } from "@/lib/api";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";

interface CostSavingsPayload {
  window_days: number;
  call_count: number;
  actual_usd: number;
  quality_baseline_usd: number;
  saved_usd: number;
  saved_pct: number;
  routing_mode: string;
  cost_guardian_enabled: boolean;
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 }).format(value);
}

/** Cost savings vs quality-first baseline — complements TimeSavedPanel on /costs. */
export function CostSavingsPanel(): JSX.Element | null {
  const { hasFeature } = usePlatform();
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [payload, setPayload] = useState<CostSavingsPayload | null>(null);

  const load = useCallback(async () => {
    try {
      const body = await hiveGet<CostSavingsPayload>("llm-routing/cost-savings?window_days=30");
      setPayload(body);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Cost savings unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useIntervalWhenVisible(() => void load(), COCKPIT_POLL_COLONY_TELEMETRY_MS, {
    enabled: hasFeature("free_first_routing"),
  });

  if (!hasFeature("free_first_routing")) {
    return null;
  }

  return (
    <V4Card className="v4-card-interactive border-(--qs-green)/30">
      <V4CardHeader
        title="LLM cost savings"
        description="Estimated spend avoided vs quality-first routing baseline"
        actions={<PiggyBank className="h-4 w-4 text-(--qs-green)" aria-hidden />}
      />

      {loading ? (
        <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading savings…
        </p>
      ) : null}

      {err ? <p className="text-sm text-(--qs-red)">{err}</p> : null}

      {!loading && !err && payload ? (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <V4Badge tone="ok">{formatUsd(payload.saved_usd)} saved</V4Badge>
            <V4Badge tone="info">{payload.saved_pct.toFixed(1)}% vs baseline</V4Badge>
            <V4Badge tone="warn">{payload.routing_mode}</V4Badge>
          </div>
          <p className="text-sm text-(--qs-text-2)">
            {payload.window_days}d · {payload.call_count} LLM calls · actual {formatUsd(payload.actual_usd)} · baseline{" "}
            {formatUsd(payload.quality_baseline_usd)}
          </p>
          {payload.cost_guardian_enabled ? (
            <p className="text-xs text-(--qs-text-3)">Cost Guardian auto-upgrade is on — cheap hops upgrade on failure.</p>
          ) : null}
        </div>
      ) : null}
    </V4Card>
  );
}
