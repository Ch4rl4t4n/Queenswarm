"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Check } from "lucide-react";

import { EnterpriseUpgradeCheckoutButton } from "@/components/hive/enterprise-upgrade-checkout-button";
import { ProUpgradeCheckoutButton } from "@/components/hive/pro-upgrade-checkout-button";
import { StripeCheckoutSettingsPanel } from "@/components/hive/stripe-checkout-settings-panel";
import { usePlatform } from "@/components/hive/platform-context";
import { V4BarRow, V4Card, V4CardHeader, V4Stat } from "@/components/ui/v4";
import type { BillingPlansPayload, BillingUsageSnapshot } from "@/lib/hive-types";
import { integrationsTabHref } from "@/lib/integrations-routes";
import { cn } from "@/lib/utils";

const ENTERPRISE_HIGHLIGHTS = [
  "White-label branding & custom domain",
  "Enterprise workspace + compliance export bundle",
  "Up to 1000 agents & 500 swarms",
  "Dedicated support channel & HA profile",
] as const;

const PRO_HIGHLIGHTS = [
  "Swarm Builder — Exec Assistant, Lead Waterfall, Content Flywheel",
  "Up to 100 agents & 50 swarms",
  "Voice Ballroom & verified recipe library",
  "Advanced memory & custom branding",
] as const;

function fmtInt(n: number): string {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(n);
}

function fmtUsd(n: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(n);
}

function fmtEurMonthly(cents: number): string {
  return `${new Intl.NumberFormat("en-EU", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(cents / 100)}/mo`;
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
  const searchParams = useSearchParams();
  const { platformMode, subscriptionTier } = usePlatform();
  const [usage, setUsage] = useState<BillingUsageSnapshot | null>(null);
  const [plans, setPlans] = useState<BillingPlansPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [upgradeNotice, setUpgradeNotice] = useState<string | null>(null);

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

  useEffect(() => {
    const upgrade = searchParams.get("upgrade");
    const sessionId = searchParams.get("session_id");

    if (upgrade === "cancel" || upgrade === "enterprise-cancel") {
      setUpgradeNotice("Checkout cancelled — no charges applied.");
      router.replace("/settings/billing");
      return;
    }

    const isProSuccess = upgrade === "success" && sessionId;
    const isEnterpriseSuccess = upgrade === "enterprise-success" && sessionId;
    if (!isProSuccess && !isEnterpriseSuccess) {
      return;
    }

    const confirmPath = isEnterpriseSuccess
      ? `/api/proxy/billing/enterprise-checkout/confirm?session_id=${encodeURIComponent(sessionId)}`
      : `/api/proxy/billing/pro-checkout/confirm?session_id=${encodeURIComponent(sessionId)}`;

    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch(confirmPath, { cache: "no-store" });
        const json = (await res.json().catch(() => ({}))) as { detail?: string; message?: string; status?: string };
        if (cancelled) return;
        if (!res.ok) {
          setUpgradeNotice(json.detail ?? "Could not confirm subscription upgrade.");
        } else if (json.status === "pending") {
          setUpgradeNotice(json.message ?? "Payment processing — refresh in a moment.");
        } else {
          setUpgradeNotice(json.message ?? "Subscription upgraded.");
          await load();
        }
      } catch {
        if (!cancelled) {
          setUpgradeNotice("Could not confirm upgrade — webhook may still apply shortly.");
        }
      } finally {
        if (!cancelled) {
          router.replace("/settings/billing");
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [load, router, searchParams]);

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

  const isCommercialFree =
    platformMode === "commercial" &&
    (subscriptionTier === "free" || usage?.tier === "free");

  const isCommercialPro =
    platformMode === "commercial" &&
    (subscriptionTier === "pro" || usage?.tier === "pro");

  const proPriceLabel = fmtEurMonthly(plans?.pro_price_eur_cents ?? 2900);
  const enterprisePriceLabel = fmtEurMonthly(plans?.enterprise_price_eur_cents ?? 9900);

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
      <StripeCheckoutSettingsPanel />

      {upgradeNotice ? (
        <V4Card tight>
          <p className="text-sm text-(--qs-green)">{upgradeNotice}</p>
        </V4Card>
      ) : null}

      {isCommercialFree ? (
        <V4Card className="border-pollen/35 bg-pollen/[0.06]">
          <V4CardHeader
            kicker="Commercial"
            title="Upgrade to Pro"
            description={`Commercial Free is limited to 2 agents and 1 swarm. Pro unlocks Swarm Builder templates (${proPriceLabel}).`}
          />
          <ul className="mb-4 flex flex-col gap-2">
            {PRO_HIGHLIGHTS.map((item) => (
              <li key={item} className="flex items-start gap-2 text-sm text-(--qs-text-2)">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-(--qs-green)" aria-hidden />
                {item}
              </li>
            ))}
          </ul>
          <div className="flex flex-wrap items-center gap-3">
            <ProUpgradeCheckoutButton
              checkoutReady={Boolean(plans?.pro_checkout_ready)}
              currentTier={usage?.tier ?? subscriptionTier}
              priceLabel={proPriceLabel}
            />
            <Link href="/swarms/new" className="qs-btn qs-btn--ghost qs-btn--sm">
              Preview Swarm Builder
            </Link>
          </div>
        </V4Card>
      ) : null}

      {isCommercialPro ? (
        <V4Card className="border-cyan/35 bg-cyan/[0.06]">
          <V4CardHeader
            kicker="Commercial"
            title="Upgrade to Enterprise"
            description={`Unlock white-label workspace, compliance bundle, and dedicated support (${enterprisePriceLabel}).`}
          />
          <ul className="mb-4 flex flex-col gap-2">
            {ENTERPRISE_HIGHLIGHTS.map((item) => (
              <li key={item} className="flex items-start gap-2 text-sm text-(--qs-text-2)">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-cyan" aria-hidden />
                {item}
              </li>
            ))}
          </ul>
          <div className="flex flex-wrap items-center gap-3">
            <EnterpriseUpgradeCheckoutButton
              checkoutReady={Boolean(plans?.enterprise_checkout_ready)}
              currentTier={usage?.tier ?? subscriptionTier}
              priceLabel={enterprisePriceLabel}
            />
            <Link href="/settings/enterprise" className="qs-btn qs-btn--ghost qs-btn--sm">
              Preview Enterprise workspace
            </Link>
          </div>
        </V4Card>
      ) : null}

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
            plans?.pro_checkout_ready && isCommercialFree ? (
              <ProUpgradeCheckoutButton
                checkoutReady
                currentTier={usage?.tier}
                priceLabel={proPriceLabel}
                size="sm"
              />
            ) : plans?.checkout_ready ? (
              <button
                type="button"
                className="qs-btn qs-btn--primary qs-btn--sm"
                onClick={() => router.push(integrationsTabHref("skills"))}
              >
                Browse premium skills
              </button>
            ) : null
          }
        />
        <p className="text-xs text-(--qs-text-3)">{plans?.message}</p>
        {usage?.upgrade_recommended ? (
          <p className="mt-2 text-xs text-(--qs-amber)">
            Soft limits exceeded — consider upgrading before hard caps block new work.
          </p>
        ) : null}
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
              {plan.tier === "pro" && isCommercialFree ? (
                <p className="mt-1 text-xs font-medium text-pollen">{proPriceLabel}</p>
              ) : null}
              {plan.tier === "enterprise" && isCommercialPro ? (
                <p className="mt-1 text-xs font-medium text-cyan">{enterprisePriceLabel}</p>
              ) : null}
              <p className="mt-2 text-xs text-(--qs-text-3)">Tokens hard: {fmtInt(plan.limits.monthly_tokens_hard ?? 0)}</p>
              <p className="text-xs text-(--qs-text-3)">Sessions hard: {fmtInt(plan.limits.monthly_supervisor_sessions_hard ?? 0)}</p>
              <p className="text-xs text-(--qs-text-3)">External calls hard: {fmtInt(plan.limits.monthly_external_calls_hard ?? 0)}</p>
              <p className="text-xs text-(--qs-text-3)">Agents hard: {fmtInt(plan.limits.max_agents_hard ?? 0)}</p>
              <p className="text-xs text-(--qs-text-3)">Swarms hard: {fmtInt(plan.limits.max_swarms_hard ?? 0)}</p>
              <p className="text-xs text-(--qs-text-3)">Storage hard: {fmtInt(plan.limits.storage_mb_hard ?? 0)} MB</p>
              <p className="mt-2 text-xs text-(--qs-text-2)">
                Features: {Object.entries(plan.features).filter(([, ok]) => ok).map(([name]) => name).join(", ")}
              </p>
              {plan.tier === "pro" && isCommercialFree ? (
                <div className="mt-3">
                  <ProUpgradeCheckoutButton
                    checkoutReady={Boolean(plans?.pro_checkout_ready)}
                    currentTier={usage?.tier}
                    priceLabel={proPriceLabel}
                    size="sm"
                  />
                </div>
              ) : null}
              {plan.tier === "enterprise" && isCommercialPro ? (
                <div className="mt-3">
                  <EnterpriseUpgradeCheckoutButton
                    checkoutReady={Boolean(plans?.enterprise_checkout_ready)}
                    currentTier={usage?.tier}
                    priceLabel={enterprisePriceLabel}
                    size="sm"
                  />
                </div>
              ) : null}
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
