"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { memo, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePatchJson } from "@/lib/api";
import { cn } from "@/lib/utils";

type PublishMode = "manual" | "auto";

interface TrustedAutoChannel {
  channel: string;
  mode: PublishMode;
  successful_simulates: number;
  min_simulates_required: number;
  auto_eligible: boolean;
}

interface TrustedAutoPolicy {
  global_enabled: boolean;
  tenant_enabled: boolean;
  min_simulates_required: number;
  live_enabled: boolean;
  channels: TrustedAutoChannel[];
}

function SettingsOperatorTrustedAutoPanelInner(): JSX.Element | null {
  const [policy, setPolicy] = useState<TrustedAutoPolicy | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<TrustedAutoPolicy>("social-publish/trusted-auto");
      setPolicy(data);
    } catch (err) {
      if (err instanceof HiveApiError && err.status === 404) {
        setPolicy(null);
        return;
      }
      setPolicy(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const patch = useCallback(
    async (body: { enabled?: boolean; channels?: Record<string, PublishMode> }) => {
      setBusy(true);
      try {
        const updated = await hivePatchJson<TrustedAutoPolicy>("social-publish/trusted-auto", body);
        setPolicy(updated);
        toast.success("Trusted auto policy saved.");
      } catch (err) {
        toast.error(err instanceof HiveApiError ? err.message : "Failed to save policy.");
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <p className="flex items-center gap-2 text-xs text-(--qs-muted)">
        <Loader2 className="size-3 animate-spin" aria-hidden />
        Loading trusted auto policy…
      </p>
    );
  }

  if (!policy) {
    return null;
  }

  const controlsDisabled = busy || !policy.global_enabled || !policy.live_enabled || !policy.tenant_enabled;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold text-(--qs-text)">Trusted auto-publish</h4>
          <p className="text-xs text-(--qs-muted)">
            Manual vs auto per channel after {policy.min_simulates_required}+ successful simulates.
          </p>
        </div>
        <button
          type="button"
          className={cn("qs-btn qs-btn--sm", policy.tenant_enabled ? "qs-btn--primary" : "qs-btn--ghost")}
          disabled={busy || !policy.global_enabled || !policy.live_enabled}
          onClick={() => void patch({ enabled: !policy.tenant_enabled })}
        >
          {busy ? <Loader2 className="size-3 animate-spin" /> : null}
          {policy.tenant_enabled ? "Auto on" : "Enable auto"}
        </button>
      </div>

      {!policy.global_enabled ? (
        <p className="text-xs text-pollen">Requires SOCIAL_PUBLISH_TRUSTED_AUTO_ENABLED=true in prod env.</p>
      ) : !policy.live_enabled ? (
        <p className="text-xs text-pollen">Requires SOCIAL_PUBLISH_LIVE_ENABLED=true before auto-live.</p>
      ) : null}

      <ul className="grid gap-2 sm:grid-cols-2">
        {policy.channels.map((row) => (
          <li
            key={row.channel}
            className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-(--qs-border)/60 px-2 py-2 text-xs"
          >
            <div>
              <span className="font-semibold capitalize text-(--qs-text)">{row.channel}</span>
              <p className="font-mono text-(--qs-muted)">
                {row.successful_simulates}/{row.min_simulates_required} simulates
                {row.auto_eligible ? <span className="ml-1 text-(--qs-green)">· ready</span> : null}
              </p>
            </div>
            <div className="flex gap-1">
              <button
                type="button"
                className={cn("qs-btn qs-btn--xs", row.mode === "manual" ? "qs-btn--primary" : "qs-btn--ghost")}
                disabled={controlsDisabled}
                onClick={() => void patch({ channels: { [row.channel]: "manual" } })}
              >
                Manual
              </button>
              <button
                type="button"
                className={cn("qs-btn qs-btn--xs", row.mode === "auto" ? "qs-btn--primary" : "qs-btn--ghost")}
                disabled={controlsDisabled || !row.auto_eligible}
                onClick={() => void patch({ channels: { [row.channel]: "auto" } })}
              >
                Auto
              </button>
            </div>
          </li>
        ))}
      </ul>

      <div className="flex flex-wrap items-center gap-2 text-xs">
        <V4Badge tone={policy.global_enabled ? "ok" : "info"}>global {policy.global_enabled ? "on" : "off"}</V4Badge>
        <V4Badge tone={policy.live_enabled ? "warn" : "ok"}>live {policy.live_enabled ? "on" : "off"}</V4Badge>
        <Link href="/integrations?tab=studio#social-publish" className="text-cyan hover:underline">
          Full panel in Execution Studio
        </Link>
      </div>
    </div>
  );
}

export const SettingsOperatorTrustedAutoPanel = memo(SettingsOperatorTrustedAutoPanelInner);
SettingsOperatorTrustedAutoPanel.displayName = "SettingsOperatorTrustedAutoPanel";
