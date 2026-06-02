"use client";

import type { JSX } from "react";

import { Copy, Link2, Loader2Icon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveDelete, hiveGet, hivePostJson } from "@/lib/api";
import { cn } from "@/lib/utils";

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
  /** Catalog cards use roomier layout for URL + enable actions. */
  variant?: "inline" | "catalog";
}

/** Enable/copy webhook ingress for one supervisor routine (Automation Ladder L4). */
export function RoutineWebhookControls({
  routineId,
  routineName,
  variant = "inline",
}: RoutineWebhookControlsProps): JSX.Element {
  const [config, setConfig] = useState<RoutineWebhookConfig | null>(null);
  const [busy, setBusy] = useState(false);
  const [freshToken, setFreshToken] = useState<string | null>(null);
  const isCatalog = variant === "catalog";

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
    <section
      className={cn(
        "v4-routine-webhook-panel space-y-3 rounded-xl border border-cyan-500/25 bg-cyan-500/[0.06]",
        isCatalog ? "p-4" : "mt-2 p-2.5",
      )}
      aria-label="Webhook ingress"
    >
      <div className="flex flex-wrap items-center gap-2">
        <Link2 className="h-4 w-4 shrink-0 text-cyan-300" aria-hidden />
        <span className="text-[11px] font-semibold uppercase tracking-wider text-cyan-200/90">Webhook (L4)</span>
        {config?.enabled ? <V4Badge tone="ok">enabled</V4Badge> : <V4Badge tone="warn">off</V4Badge>}
        {config && config.trigger_count > 0 ? (
          <span className="text-[10px] text-(--qs-text-4)">{config.trigger_count} triggers</span>
        ) : null}
      </div>

      {config?.webhook_url ? (
        <div className="flex min-w-0 items-start gap-2 rounded-lg border border-[color:var(--qs-border)]/60 bg-black/35 p-2.5">
          <p className="min-w-0 flex-1 break-all font-(family-name:--font-jetbrains-mono) text-[10px] leading-relaxed text-(--qs-text-2) sm:text-[11px]">
            {config.webhook_url}
          </p>
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm shrink-0 px-2"
            aria-label="Copy webhook URL"
            onClick={() => void copyText("Webhook URL", config.webhook_url)}
          >
            <Copy className="h-3.5 w-3.5" aria-hidden />
          </button>
        </div>
      ) : (
        <p className="text-[11px] leading-relaxed text-(--qs-text-3)">
          Enable webhook ingress to trigger this routine from Make, n8n, or any HTTP client.
        </p>
      )}

      {freshToken ? (
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm w-full justify-start gap-2 font-(family-name:--font-jetbrains-mono) text-[10px] text-pollen"
          onClick={() => void copyText("Webhook token", freshToken)}
        >
          <Copy className="h-3.5 w-3.5 shrink-0" aria-hidden />
          Token (copy now — shown once)
        </button>
      ) : null}

      {config?.make_hint ? (
        <p className="text-[10px] leading-relaxed text-(--qs-text-4)">{config.make_hint}</p>
      ) : null}

      <div className={cn("flex flex-wrap gap-2", isCatalog && "pt-1")}>
        <button
          type="button"
          className={cn("qs-btn qs-btn--primary qs-btn--sm", isCatalog && "min-h-10 flex-1 justify-center sm:flex-none")}
          disabled={busy}
          onClick={() => void enableWebhook()}
        >
          {busy ? <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden /> : "Enable / rotate"}
        </button>
        {config?.enabled ? (
          <button
            type="button"
            className={cn("qs-btn qs-btn--ghost qs-btn--sm", isCatalog && "min-h-10 flex-1 justify-center sm:flex-none")}
            disabled={busy}
            onClick={() => void disableWebhook()}
          >
            Disable
          </button>
        ) : null}
      </div>
    </section>
  );
}
