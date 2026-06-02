"use client";

import type { JSX } from "react";

import { Copy, Link2, Loader2Icon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveDelete, hiveGet, hivePostJson } from "@/lib/api";

interface RoutineWebhookConfig {
  routine_id: string;
  enabled: boolean;
  webhook_url: string;
  has_token: boolean;
  last_received_at: string | null;
  trigger_count: number;
  make_hint: string;
}

interface RoutineWebhookEnableResponse {
  routine_id: string;
  webhook_url: string;
  token: string;
  curl_example: string;
}

interface RoutineWebhookControlsProps {
  routineId: string;
  routineName: string;
}

/** Enable/copy webhook ingress for one supervisor routine (Automation Ladder L4). */
export function RoutineWebhookControls({ routineId, routineName }: RoutineWebhookControlsProps): JSX.Element {
  const [config, setConfig] = useState<RoutineWebhookConfig | null>(null);
  const [busy, setBusy] = useState(false);
  const [freshToken, setFreshToken] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const row = await hiveGet<RoutineWebhookConfig>(
        `agents/routines/${encodeURIComponent(routineId)}/webhook-config`,
      );
      setConfig(row);
    } catch {
      setConfig(null);
    }
  }, [routineId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function enableWebhook(): Promise<void> {
    setBusy(true);
    try {
      const res = await hivePostJson<RoutineWebhookEnableResponse>(
        `agents/routines/${encodeURIComponent(routineId)}/webhook/enable`,
        {},
      );
      setFreshToken(res.token);
      toast.success(`Webhook enabled for ${routineName}`);
      await load();
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Webhook enable failed");
    } finally {
      setBusy(false);
    }
  }

  async function disableWebhook(): Promise<void> {
    setBusy(true);
    try {
      await hiveDelete(`agents/routines/${encodeURIComponent(routineId)}/webhook`);
      setFreshToken(null);
      toast.message("Webhook disabled");
      await load();
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Webhook disable failed");
    } finally {
      setBusy(false);
    }
  }

  async function copyText(label: string, value: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(value);
      toast.success(`${label} copied`);
    } catch {
      toast.error("Copy failed");
    }
  }

  return (
    <div className="mt-2 space-y-2 rounded-lg border border-cyan-500/20 bg-cyan-500/5 p-2.5">
      <div className="flex flex-wrap items-center gap-2">
        <Link2 className="h-3.5 w-3.5 text-cyan-300" aria-hidden />
        <span className="text-[10px] font-semibold uppercase tracking-wider text-cyan-200/90">
          Webhook (L4)
        </span>
        {config?.enabled ? <V4Badge tone="ok">enabled</V4Badge> : <V4Badge tone="warn">off</V4Badge>}
        {config && config.trigger_count > 0 ? (
          <span className="text-[10px] text-(--qs-text-4)">{config.trigger_count} triggers</span>
        ) : null}
      </div>
      {config?.webhook_url ? (
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm w-full justify-start truncate font-(family-name:--font-jetbrains-mono) text-[10px]"
          onClick={() => void copyText("Webhook URL", config.webhook_url)}
        >
          <Copy className="mr-1 h-3 w-3 shrink-0" aria-hidden />
          {config.webhook_url}
        </button>
      ) : null}
      {freshToken ? (
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm w-full justify-start truncate font-(family-name:--font-jetbrains-mono) text-[10px] text-pollen"
          onClick={() => void copyText("Webhook token", freshToken)}
        >
          <Copy className="mr-1 h-3 w-3 shrink-0" aria-hidden />
          Token (copy now — shown once)
        </button>
      ) : null}
      {config?.make_hint ? <p className="text-[10px] text-(--qs-text-4)">{config.make_hint}</p> : null}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="qs-btn qs-btn--primary qs-btn--sm"
          disabled={busy}
          onClick={() => void enableWebhook()}
        >
          {busy ? <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden /> : "Enable / rotate"}
        </button>
        {config?.enabled ? (
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" disabled={busy} onClick={() => void disableWebhook()}>
            Disable
          </button>
        ) : null}
      </div>
    </div>
  );
}
