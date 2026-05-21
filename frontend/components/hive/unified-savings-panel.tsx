"use client";

import { ClockIcon, Loader2Icon, PiggyBank, Sparkles } from "lucide-react";
import { useCallback, useState } from "react";

import { usePlatform } from "@/components/hive/platform-context";
import { V4Badge, V4Card, V4CardHeader, V4Stat } from "@/components/ui/v4";
import { COCKPIT_POLL_COLONY_TELEMETRY_MS } from "@/lib/cockpit-poll-profile";
import { HiveApiError, hiveGet } from "@/lib/api";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";
import type { UnifiedSavingsPayload } from "@/lib/hive-types";

function fmtHours(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  if (value < 1) {
    return `${Math.round(value * 60)}m`;
  }
  return `${value.toFixed(1)}h`;
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 }).format(value);
}

/** Merged verified time ROI + LLM cost savings — primary widget on /costs. */
export function UnifiedSavingsPanel(): JSX.Element {
  const { hasFeature } = usePlatform();
  const [payload, setPayload] = useState<UnifiedSavingsPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const body = await hiveGet<UnifiedSavingsPayload>("dashboard/unified-savings?window_days=30");
      setPayload(body);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Unified savings unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useIntervalWhenVisible(() => void load(), COCKPIT_POLL_COLONY_TELEMETRY_MS);

  const showLlm = Boolean(payload?.llm_savings_available && hasFeature("free_first_routing"));
  const headline = payload?.headline;
  const timeSaved = payload?.time_saved;
  const llmSavings = payload?.llm_savings;

  return (
    <V4Card className="v4-card-interactive border-(--qs-green)/25 bg-linear-to-br from-(--qs-green)/5 to-transparent">
      <V4CardHeader
        title="Unified savings"
        description="Verified workflow time + LLM spend avoided vs quality baseline"
        actions={
          <V4Badge tone="ok">
            <Sparkles className="mr-1 inline h-3 w-3" aria-hidden />
            30d
          </V4Badge>
        }
      />

      {loading ? (
        <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Calculating total value…
        </p>
      ) : null}

      {err ? <p className="text-sm text-(--qs-red)">{err}</p> : null}

      {!loading && !err && payload && headline ? (
        <div className="space-y-6">
          <div className="rounded-xl border border-(--qs-gold)/30 bg-(--qs-gold)/5 px-4 py-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-(--qs-gold)">Total estimated value</p>
            <p className="mt-1 font-mono text-3xl font-semibold text-(--qs-text) tabular-nums">
              {formatUsd(headline.total_value_usd)}
            </p>
            <p className="mt-2 text-xs text-(--qs-text-3)">
              {formatUsd(headline.time_value_usd)} time @ {formatUsd(payload.hourly_rate_usd)}/hr
              {showLlm && llmSavings ? ` · ${formatUsd(headline.llm_saved_usd)} LLM` : null}
            </p>
          </div>

          <div className="v4-stat-grid">
            <V4Stat
              label="Hours saved"
              value={fmtHours(headline.hours_saved_total)}
              foot={`${headline.verified_task_count} verified tasks`}
              valueVariant="gold"
            />
            <V4Stat
              label="Projected / month"
              value={fmtHours(headline.hours_saved_projected_monthly)}
              foot="Time ROI scaled"
            />
            {showLlm && llmSavings ? (
              <V4Stat
                label="LLM saved"
                value={formatUsd(headline.llm_saved_usd)}
                foot={`${headline.llm_saved_pct?.toFixed(1) ?? "0"}% vs baseline`}
                valueVariant="gold"
              />
            ) : (
              <V4Stat label="LLM routing" value="—" foot="Enable Free-First for cost lane" />
            )}
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <section className="space-y-3 rounded-xl border border-(--qs-border)/60 bg-black/20 p-4">
              <div className="flex items-center gap-2">
                <ClockIcon className="h-4 w-4 text-(--qs-cyan)" aria-hidden />
                <p className="text-sm font-semibold text-(--qs-text)">Time saved breakdown</p>
              </div>
              {!timeSaved?.breakdown.length ? (
                <p className="text-xs text-(--qs-text-3)">No verified tasks with pollen in this window yet.</p>
              ) : (
                <ul className="space-y-2">
                  {timeSaved.breakdown.slice(0, 5).map((row) => (
                    <li
                      key={`${row.source_kind}:${row.source_key}`}
                      className="flex items-center justify-between gap-2 text-xs"
                    >
                      <span className="text-(--qs-text-2)">{row.source_label}</span>
                      <span className="font-mono text-pollen">{fmtHours(row.hours_saved)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {showLlm && llmSavings ? (
              <section className="space-y-3 rounded-xl border border-(--qs-green)/30 bg-black/20 p-4">
                <div className="flex items-center gap-2">
                  <PiggyBank className="h-4 w-4 text-(--qs-green)" aria-hidden />
                  <p className="text-sm font-semibold text-(--qs-text)">LLM cost lane</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <V4Badge tone="ok">{formatUsd(llmSavings.saved_usd)} saved</V4Badge>
                  <V4Badge tone="info">{llmSavings.saved_pct.toFixed(1)}% vs baseline</V4Badge>
                  <V4Badge tone="warn">{llmSavings.routing_mode}</V4Badge>
                </div>
                <p className="text-xs text-(--qs-text-3)">
                  {llmSavings.window_days}d · {llmSavings.call_count} calls · actual {formatUsd(llmSavings.actual_usd)} ·
                  baseline {formatUsd(llmSavings.quality_baseline_usd)}
                </p>
                {llmSavings.cost_guardian_enabled ? (
                  <p className="text-[10px] text-(--qs-text-3)">Cost Guardian auto-upgrade active.</p>
                ) : null}
              </section>
            ) : (
              <section className="flex items-center rounded-xl border border-dashed border-(--qs-border)/60 p-4 text-xs text-(--qs-text-3)">
                Enable Free-First routing in Settings → AI keys to unlock LLM savings in this dashboard.
              </section>
            )}
          </div>

          <p className="text-[10px] text-(--qs-text-3)">{payload.disclaimer}</p>
        </div>
      ) : null}
    </V4Card>
  );
}
