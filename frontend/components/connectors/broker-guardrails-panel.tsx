"use client";

import { Loader2, Shield, ShieldOff } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePatchJson } from "@/lib/api";

type ApproveMode = "always" | "simulate_first" | "trusted_auto";

interface BrokerGuardrailsSnapshot {
  enabled: boolean;
  kill_switch: boolean;
  max_order_usd: number;
  daily_cap_usd: number;
  approve_mode: ApproveMode;
  venues: string[];
  daily_spent_usd: number;
  daily_spend_date: string | null;
  source: "deployment" | "tenant";
}

const APPROVE_MODE_OPTIONS: { value: ApproveMode; label: string }[] = [
  { value: "always", label: "Always approve (HITL)" },
  { value: "simulate_first", label: "Simulate first" },
  { value: "trusted_auto", label: "Trusted auto (after simulates)" },
];

export function BrokerGuardrailsPanel(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<BrokerGuardrailsSnapshot | null>(null);
  const [draft, setDraft] = useState<BrokerGuardrailsSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<BrokerGuardrailsSnapshot>("trading-cockpit/guardrails");
      setSnapshot(data);
      setDraft(data);
    } catch {
      setSnapshot(null);
      setDraft(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const save = useCallback(async () => {
    if (!draft) return;
    setSaving(true);
    try {
      const data = await hivePatchJson<BrokerGuardrailsSnapshot>("trading-cockpit/guardrails", {
        enabled: draft.enabled,
        kill_switch: draft.kill_switch,
        max_order_usd: draft.max_order_usd,
        daily_cap_usd: draft.daily_cap_usd,
        approve_mode: draft.approve_mode,
        venues: draft.venues,
      });
      setSnapshot(data);
      setDraft(data);
      toast.success("Broker guardrails saved.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }, [draft]);

  if (loading) {
    return (
      <V4Card className="flex items-center gap-2 p-4 text-sm text-white/60" data-testid="broker-guardrails-panel">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Loading broker guardrails…
      </V4Card>
    );
  }

  if (!draft) {
    return null;
  }

  const dailyUtil =
    draft.daily_cap_usd > 0 ? Math.min(100, Math.round((draft.daily_spent_usd / draft.daily_cap_usd) * 100)) : 0;

  return (
    <V4Card id="broker-guardrails" className="border-magenta-500/25" data-testid="broker-guardrails-panel">
      <V4CardHeader
        kicker="Track P · RA3"
        title="Broker guardrails"
        description="Shared caps for Polymarket and Robinhood — max order, daily spend, kill switch, approve mode."
        actions={
          <div className="flex items-center gap-2">
            <V4Badge tone={draft.kill_switch ? "err" : draft.enabled ? "ok" : "warn"}>
              {draft.kill_switch ? "Kill switch ON" : draft.enabled ? "Active" : "Off"}
            </V4Badge>
            <HiveRefreshButton busy={loading} onClick={() => void load()} />
          </div>
        }
      />
      <div className="space-y-4 px-4 pb-4">
        <label className="flex items-center gap-2 text-sm text-white/80">
          <input
            type="checkbox"
            checked={draft.enabled}
            onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })}
          />
          Enable broker guardrails pack
        </label>
        <label className="flex items-center gap-2 text-sm text-(--qs-magenta)">
          <input
            type="checkbox"
            checked={draft.kill_switch}
            onChange={(e) => setDraft({ ...draft, kill_switch: e.target.checked })}
          />
          Kill switch — block all live broker orders
        </label>

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="text-white/60">Max order (USD)</span>
            <input
              type="number"
              min={1}
              className="qs-input mt-1 w-full font-mono"
              value={draft.max_order_usd}
              onChange={(e) => setDraft({ ...draft, max_order_usd: Number(e.target.value) })}
            />
          </label>
          <label className="block text-sm">
            <span className="text-white/60">Daily cap (USD)</span>
            <input
              type="number"
              min={10}
              className="qs-input mt-1 w-full font-mono"
              value={draft.daily_cap_usd}
              onChange={(e) => setDraft({ ...draft, daily_cap_usd: Number(e.target.value) })}
            />
          </label>
          <label className="block text-sm sm:col-span-2">
            <span className="text-white/60">Approve mode</span>
            <select
              className="qs-input mt-1 w-full font-mono"
              value={draft.approve_mode}
              onChange={(e) => setDraft({ ...draft, approve_mode: e.target.value as ApproveMode })}
            >
              {APPROVE_MODE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-white/80">Venues</p>
          <div className="flex flex-wrap gap-3">
            {(["polymarket", "robinhood"] as const).map((venue) => (
              <label key={venue} className="flex items-center gap-2 text-sm capitalize text-white/70">
                <input
                  type="checkbox"
                  checked={draft.venues.includes(venue)}
                  onChange={(e) => {
                    const next = e.target.checked
                      ? [...draft.venues, venue]
                      : draft.venues.filter((row) => row !== venue);
                    if (next.length === 0) return;
                    setDraft({ ...draft, venues: next });
                  }}
                />
                {venue}
              </label>
            ))}
          </div>
        </div>

        <p className="text-xs font-mono text-white/50">
          Today: ${draft.daily_spent_usd.toFixed(2)} / ${draft.daily_cap_usd.toFixed(2)} ({dailyUtil}%)
        </p>
        <p className="text-xs text-white/50">Source: {snapshot?.source ?? draft.source}. Syncs trading lane risk caps on save.</p>

        <button
          type="button"
          className="qs-btn qs-btn--primary qs-btn--sm inline-flex gap-1.5"
          disabled={saving}
          onClick={() => void save()}
        >
          {saving ? (
            <Loader2 className="size-4 animate-spin" />
          ) : draft.kill_switch ? (
            <ShieldOff className="size-4" />
          ) : (
            <Shield className="size-4" />
          )}
          Save guardrails
        </button>
      </div>
    </V4Card>
  );
}
