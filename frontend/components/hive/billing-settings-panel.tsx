"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { V4BarRow, V4Card, V4CardHeader, V4Stat } from "@/components/ui/v4";
import type { BillingPlansPayload, BillingUsageSnapshot } from "@/lib/hive-types";
import { integrationsTabHref } from "@/lib/integrations-routes";
import { cn } from "@/lib/utils";

function fmtInt(n: number): string {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(n);
}

function fmtUsd(n: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(n);
}

function healthTone(row: { hard_exceeded: boolean; soft_exceeded: boolean }): "ok" | "warn" | "err" {
  if (row.hard_exceeded) return "err";
  if (row.soft_exceeded) return "warn";
  return "ok";
}

function healthLabel(row: { hard_exceeded: boolean; soft_exceeded: boolean }): string {
  if (row.hard_exceeded) return "hard exceeded";
  if (row.soft_exceeded) return "soft exceeded";
  return "healthy";
}

export function BillingSettingsPanel() {
  const router = useRouter();
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
    return (
      <V4Card>
        <p className="text-sm text-(--qs-text-3)">Loading billing…</p>
      </V4Card>
    );
  }
  if (error && !usage) {
    return (
      <V4Card>
        <p className="text-sm text-(--qs-red)">{error}</p>
      </V4Card>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <V4Card>
        <V4CardHeader
          title="Usage & Billing"
          description={
            <>
              Current plan: <span className="text-(--qs-amber)">{usage?.tier ?? "free"}</span> · status:{" "}
              <span className="text-(--qs-text-2)">{usage?.status ?? "active"}</span>
            </>
          }
          actions={
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm"
              onClick={() => {
                if (plans?.checkout_ready) {
                  router.push(integrationsTabHref("skills"));
                  return;
                }
                router.push("/settings/billing");
              }}
            >
              {plans?.checkout_ready ? "Browse premium skills" : "View plan limits"}
            </button>
          }
        />
        <p className="text-xs text-(--qs-text-3)">
          {plans?.checkout_ready
            ? "Stripe is configured — premium skill one-time checkout is available under Integrations → Skills export."
            : "Set STRIPE_SECRET_KEY to enable premium skill checkout; subscription billing remains optional."}
        </p>
      </V4Card>

      <div className="v4-stat-grid">
        {topMetrics.map((metric) => (
          <V4Stat key={metric.key} label={metric.label} value={metric.value} valueVariant="text" />
        ))}
      </div>

      <V4Card>
        <V4CardHeader title="Soft/Hard limits" description="Usage health against tier soft and hard caps." />
        <div className="flex flex-col gap-3">
          {Object.entries(usage?.usage_health ?? {}).map(([metric, row]) => (
            <div key={metric} className="rounded-(--qs-radius-sm) border border-(--qs-border) bg-white/2 p-3">
              <div className="mb-2 flex justify-end">
                <span
                  className={cn(
                    "text-xs",
                    healthTone(row) === "err"
                      ? "text-(--qs-red)"
                      : healthTone(row) === "warn"
                        ? "text-(--qs-amber)"
                        : "text-(--qs-text-3)",
                  )}
                >
                  {healthLabel(row)}
                </span>
              </div>
              <V4BarRow
                label={metric}
                value={`${fmtInt(row.value)} / ${fmtInt(row.hard_limit)}`}
                pct={row.hard_pct}
              />
              <p className="mt-1 text-xs text-(--qs-text-3)">
                soft {fmtInt(row.soft_limit)} · hard {fmtInt(row.hard_limit)}
              </p>
            </div>
          ))}
        </div>
      </V4Card>

      <V4Card>
        <V4CardHeader title="Plan comparison" description="Tier limits and enabled features." />
        <div className="v4-settings-billing-plans grid gap-3 lg:grid-cols-3">
          {(plans?.plans ?? []).map((plan) => (
            <article
              key={plan.tier}
              className={cn(
                "rounded-(--qs-radius-sm) border p-4",
                plan.tier === usage?.tier
                  ? "border-(--qs-amber)/45 bg-(--qs-amber)/6"
                  : "border-(--qs-border) bg-white/2",
              )}
            >
              <p className="text-sm font-semibold text-(--qs-text)">{plan.label}</p>
              <p className="mt-2 text-xs text-(--qs-text-3)">Tokens hard: {fmtInt(plan.limits.monthly_tokens_hard ?? 0)}</p>
              <p className="text-xs text-(--qs-text-3)">Sessions hard: {fmtInt(plan.limits.monthly_supervisor_sessions_hard ?? 0)}</p>
              <p className="text-xs text-(--qs-text-3)">External calls hard: {fmtInt(plan.limits.monthly_external_calls_hard ?? 0)}</p>
              <p className="text-xs text-(--qs-text-3)">Storage hard: {fmtInt(plan.limits.storage_mb_hard ?? 0)} MB</p>
              <p className="mt-2 text-xs text-(--qs-text-2)">
                Features: {Object.entries(plan.features).filter(([, ok]) => ok).map(([name]) => name).join(", ")}
              </p>
            </article>
          ))}
        </div>
      </V4Card>

      <V4Card tight>
        <p className="text-sm text-(--qs-text-2)">
          Monthly LLM spend estimate:{" "}
          <span className="font-semibold text-(--qs-text)">{fmtUsd(usage?.usage.monthly_spend_usd ?? 0)}</span>
        </p>
      </V4Card>

      {error ? <p className="text-sm text-(--qs-red)">{error}</p> : null}
    </div>
  );
}
