"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import type { BillingPlansPayload, BillingUsageSnapshot } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

function fmtInt(n: number): string {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(n);
}

function fmtUsd(n: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(n);
}

export function BillingSettingsPanel() {
  const [usage, setUsage] = useState<BillingUsageSnapshot | null>(null);
  const [plans, setPlans] = useState<BillingPlansPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [usageRes, plansRes] = await Promise.all([
        fetch("/api/proxy/billing/usage", { cache: "no-store" }),
        fetch("/api/proxy/billing/plans", { cache: "no-store" }),
      ]);
      const usageJson = (await usageRes.json().catch(() => ({}))) as BillingUsageSnapshot | { detail?: string };
      const plansJson = (await plansRes.json().catch(() => ({}))) as BillingPlansPayload | { detail?: string };
      if (!usageRes.ok) {
        throw new Error("detail" in usageJson ? String(usageJson.detail) : "Usage load failed");
      }
      if (!plansRes.ok) {
        throw new Error("detail" in plansJson ? String(plansJson.detail) : "Plans load failed");
      }
      setUsage(usageJson as BillingUsageSnapshot);
      setPlans(plansJson as BillingPlansPayload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load billing data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const topMetrics = useMemo(() => {
    if (!usage) {
      return [];
    }
    return [
      {
        key: "monthly_tokens",
        label: "LLM tokens / month",
        value: fmtInt(usage.usage.monthly_tokens ?? 0),
      },
      {
        key: "monthly_supervisor_sessions",
        label: "Supervisor sessions / month",
        value: fmtInt(usage.usage.monthly_supervisor_sessions ?? 0),
      },
      {
        key: "monthly_external_calls",
        label: "External API calls / month",
        value: fmtInt(usage.usage.monthly_external_calls ?? 0),
      },
      {
        key: "storage_mb_estimate",
        label: "Storage estimate",
        value: `${(usage.usage.storage_mb_estimate ?? 0).toFixed(2)} MB`,
      },
    ];
  }, [usage]);

  if (loading) {
    return <div className="rounded-2xl border border-cyan/20 bg-hive-card/70 p-5 text-sm text-zinc-400">Loading billing…</div>;
  }
  if (error && !usage) {
    return <div className="rounded-2xl border border-rose-500/30 bg-rose-950/30 p-5 text-sm text-rose-200">{error}</div>;
  }

  return (
    <section className="space-y-6">
      <header className="rounded-2xl border border-cyan/15 bg-hive-card/70 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-zinc-100">Usage & Billing</h2>
            <p className="mt-1 text-sm text-zinc-400">
              Current plan: <span className="text-amber-300">{usage?.tier ?? "free"}</span> · status:{" "}
              <span className="text-cyan-300">{usage?.status ?? "active"}</span>
            </p>
          </div>
          <button
            type="button"
            className="rounded-xl bg-amber-400 px-4 py-2 text-sm font-semibold text-black transition hover:bg-amber-300"
          >
            Upgrade plan
          </button>
        </div>
        <p className="mt-2 text-xs text-zinc-500">Stripe checkout wiring is prepared, but payment activation is intentionally deferred.</p>
      </header>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {topMetrics.map((metric) => (
          <article key={metric.key} className="rounded-2xl border border-cyan/10 bg-hive-card/70 p-4">
            <p className="text-xs uppercase tracking-wide text-zinc-500">{metric.label}</p>
            <p className="mt-2 text-xl font-semibold text-zinc-100">{metric.value}</p>
          </article>
        ))}
      </div>

      <div className="rounded-2xl border border-cyan/15 bg-hive-card/70 p-5">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-200">Soft/Hard limits</h3>
        <div className="mt-4 space-y-3">
          {Object.entries(usage?.usage_health ?? {}).map(([metric, row]) => (
            <div key={metric} className="rounded-xl border border-cyan/10 p-3">
              <div className="flex items-center justify-between gap-2 text-sm">
                <span className="text-zinc-200">{metric}</span>
                <span className={cn("text-xs", row.hard_exceeded ? "text-rose-300" : row.soft_exceeded ? "text-amber-300" : "text-zinc-500")}>
                  {row.hard_exceeded ? "hard exceeded" : row.soft_exceeded ? "soft exceeded" : "healthy"}
                </span>
              </div>
              <p className="mt-1 text-xs text-zinc-500">
                value {fmtInt(row.value)} · soft {fmtInt(row.soft_limit)} · hard {fmtInt(row.hard_limit)}
              </p>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-black/40">
                <div
                  className={cn(
                    "h-full rounded-full",
                    row.hard_exceeded ? "bg-rose-400" : row.soft_exceeded ? "bg-amber-400" : "bg-cyan-400",
                  )}
                  style={{ width: `${Math.min(100, row.hard_pct)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-cyan/15 bg-hive-card/70 p-5">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-200">Plan comparison</h3>
        <div className="mt-4 grid gap-3 lg:grid-cols-3">
          {(plans?.plans ?? []).map((plan) => (
            <article
              key={plan.tier}
              className={cn(
                "rounded-xl border p-4",
                plan.tier === usage?.tier ? "border-amber-400/60 bg-amber-500/10" : "border-cyan/15 bg-hive-void/50",
              )}
            >
              <p className="text-sm font-semibold text-zinc-100">{plan.label}</p>
              <p className="mt-2 text-xs text-zinc-500">Tokens hard: {fmtInt(plan.limits.monthly_tokens_hard ?? 0)}</p>
              <p className="text-xs text-zinc-500">Sessions hard: {fmtInt(plan.limits.monthly_supervisor_sessions_hard ?? 0)}</p>
              <p className="text-xs text-zinc-500">External calls hard: {fmtInt(plan.limits.monthly_external_calls_hard ?? 0)}</p>
              <p className="text-xs text-zinc-500">Storage hard: {fmtInt(plan.limits.storage_mb_hard ?? 0)} MB</p>
              <p className="mt-2 text-xs text-zinc-400">
                Features: {Object.entries(plan.features).filter(([, ok]) => ok).map(([name]) => name).join(", ")}
              </p>
            </article>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-cyan/15 bg-hive-card/70 p-5 text-sm text-zinc-300">
        Monthly LLM spend estimate: <span className="text-cyan-300">{fmtUsd(usage?.usage.monthly_spend_usd ?? 0)}</span>
      </div>
      {error ? <p className="text-sm text-rose-300">{error}</p> : null}
    </section>
  );
}
