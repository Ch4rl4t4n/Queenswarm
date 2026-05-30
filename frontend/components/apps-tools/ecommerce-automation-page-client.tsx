"use client";

import { Package, ShoppingCart, Webhook } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ModulePolicyPackPill } from "@/components/apps-tools/module-policy-pack-pill";
import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HiveSubnavRow } from "@/components/hive/hive-subnav-row";
import { HiveApiError, hiveGet } from "@/lib/api";

interface CommerceOrderEvent {
  provider: "stripe" | "shopify";
  event_id: string;
  event_type: string;
  object_id: string;
  amount_cents: number | null;
  currency: string | null;
  customer_id: string | null;
  order_status: string | null;
  ingested_at: string;
}

type EcommerceSection = "orders" | "setup";

function formatAmount(cents: number | null, currency: string | null): string {
  if (cents === null) return "—";
  const amount = (cents / 100).toFixed(2);
  return currency ? `${amount} ${currency.toUpperCase()}` : amount;
}

export function EcommerceAutomationPageClient() {
  const [section, setSection] = useState<EcommerceSection>("orders");
  const [events, setEvents] = useState<CommerceOrderEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadEvents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await hiveGet<CommerceOrderEvent[]>("/commerce/order-events?limit=50");
      setEvents(Array.isArray(rows) ? rows : []);
    } catch (err) {
      const message = err instanceof HiveApiError ? err.message : "Failed to load order events.";
      setError(message);
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (section === "orders") {
      void loadEvents();
    }
  }, [section, loadEvents]);

  return (
    <HivePageShell
      title="E-commerce Ops"
      subtitle="Shopify + Stripe order sync, webhook queue, and eshop-ops swarm handoff — simulate-first, operator approval for live mutations."
      status={<ModulePolicyPackPill moduleKey="ecommerce_workspace" />}
      error={error ? { message: error, onDismiss: () => setError(null) } : null}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link href="/integrations?tab=connectors" className="qs-btn qs-btn--ghost qs-btn--sm">
            Connectors
          </Link>
          <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" onClick={() => void loadEvents()}>
            Refresh
          </button>
        </div>
      }
      subnav={
        <HiveSubnavRow
          items={[
            { id: "orders", label: "Order events", icon: Package },
            { id: "setup", label: "Setup", icon: Webhook },
          ]}
          activeId={section}
          onChange={(id) => setSection(id as EcommerceSection)}
          ariaLabel="E-commerce automation sections"
          menuKey="apps-tools-ecommerce-automation"
        />
      }
    >
      {section === "orders" ? (
        <div className="qs-bubble space-y-4 p-4">
          <div className="flex items-center gap-2 text-sm text-white/70">
            <ShoppingCart className="size-4 text-[#00E5FF]" aria-hidden />
            <span>Recent webhook events (Stripe ingress → Redis → swarm_events)</span>
          </div>
          {loading ? (
            <div className="animate-pulse space-y-2" aria-busy="true">
              <div className="h-10 rounded bg-white/5" />
              <div className="h-10 rounded bg-white/5" />
            </div>
          ) : events.length === 0 ? (
            <p className="text-sm text-white/60">
              No order events yet. Enable{" "}
              <code className="font-mono text-[#00FFFF]">COMMERCE_WEBHOOKS_ENABLED</code> and point Stripe to{" "}
              <code className="font-mono text-[#00FFFF]">/api/v1/commerce/webhooks/stripe</code>.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-white/50">
                    <th className="py-2 pr-3 font-medium">Ingested</th>
                    <th className="py-2 pr-3 font-medium">Provider</th>
                    <th className="py-2 pr-3 font-medium">Type</th>
                    <th className="py-2 pr-3 font-medium">Amount</th>
                    <th className="py-2 pr-3 font-medium">Status</th>
                    <th className="py-2 font-medium">Event ID</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((row) => (
                    <tr key={`${row.provider}:${row.event_id}`} className="border-b border-white/5">
                      <td className="py-2 pr-3 font-mono text-xs text-white/70">{row.ingested_at.slice(0, 19)}</td>
                      <td className="py-2 pr-3 capitalize">{row.provider}</td>
                      <td className="py-2 pr-3 font-mono text-xs">{row.event_type}</td>
                      <td className="py-2 pr-3">{formatAmount(row.amount_cents, row.currency)}</td>
                      <td className="py-2 pr-3">{row.order_status ?? "—"}</td>
                      <td className="py-2 font-mono text-xs text-white/60">{row.event_id}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : null}
      {section === "setup" ? (
        <div className="qs-bubble space-y-3 p-4 text-sm text-white/80">
          <p>1. Seal Shopify + Stripe API keys in Integrations → Connector Vault.</p>
          <p>2. Set Stripe webhook URL to your domain + <code className="font-mono text-[#00FFFF]">/api/v1/commerce/webhooks/stripe</code>.</p>
          <p>3. Enable <code className="font-mono text-[#00FFFF]">COMMERCE_WEBHOOKS_ENABLED=true</code> and configure signing secret.</p>
          <p>4. Create <strong>E-shop Ops</strong> swarm via Swarm Builder — Order Monitor Bee consumes this queue.</p>
          <p className="text-[#FFB800]">Live Shopify/Stripe mutations require operator approval (real-money-risk-gate).</p>
        </div>
      ) : null}
    </HivePageShell>
  );
}
