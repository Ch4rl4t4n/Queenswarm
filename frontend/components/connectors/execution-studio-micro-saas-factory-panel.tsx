"use client";

import { Factory, Loader2, RefreshCw } from "lucide-react";
import Link from "next/link";
import { memo, useCallback, useEffect, useState } from "react";

import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";

interface MicroSaasStep {
  id: string;
  label: string;
  status: string;
  detail: string;
}

interface MicroSaasAction {
  id: string;
  label: string;
  detail: string;
  priority: string;
  href?: string | null;
}

interface MicroSaasSnapshot {
  enabled: boolean;
  progress_pct: number;
  product_name: string;
  stripe_ready: boolean;
  deploy_domain: string;
  steps: MicroSaasStep[];
  actions: MicroSaasAction[];
}

export interface ExecutionStudioMicroSaasFactoryPanelProps {
  onError: (message: string | null) => void;
}

function stepTone(status: string): "ok" | "warn" | "info" {
  if (status === "done") return "ok";
  if (status === "pending") return "info";
  return "warn";
}

function ExecutionStudioMicroSaasFactoryPanelInner({ onError }: ExecutionStudioMicroSaasFactoryPanelProps) {
  const [snapshot, setSnapshot] = useState<MicroSaasSnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    onError(null);
    try {
      const data = await hiveGet<MicroSaasSnapshot>("micro-saas-factory");
      setSnapshot(data);
    } catch (err) {
      if (err instanceof HiveApiError && err.status === 404) {
        setSnapshot(null);
        return;
      }
      onError(err instanceof Error ? err.message : "Micro-SaaS factory snapshot failed.");
    } finally {
      setLoading(false);
    }
  }, [onError]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!loading && snapshot && !snapshot.enabled) {
    return null;
  }

  return (
    <div id="micro-saas-factory" className="qs-bubble qs-bubble--tint-cyan shrink-0 space-y-3 p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Factory className="size-4 text-cyan" aria-hidden />
          <h3 className="font-heading text-sm font-semibold text-(--qs-text)">Micro-SaaS Factory</h3>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-md p-1 text-(--qs-text-3) hover:text-cyan"
          aria-label="Refresh factory snapshot"
        >
          {loading ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
        </button>
      </div>

      {loading && !snapshot ? (
        <p className="text-xs text-(--qs-text-3)">Loading factory checklist…</p>
      ) : snapshot ? (
        <>
          <div className="flex flex-wrap gap-2 text-xs">
            <V4Badge tone="info">{snapshot.product_name}</V4Badge>
            <V4Badge tone={snapshot.progress_pct >= 75 ? "ok" : "warn"}>{snapshot.progress_pct}% ready</V4Badge>
            {snapshot.stripe_ready ? <V4Badge tone="ok">Stripe</V4Badge> : null}
          </div>

          <ul className="space-y-1 text-xs">
            {snapshot.steps.map((step) => (
              <li key={step.id} className="rounded bg-black/20 px-2 py-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-(--qs-text)">{step.label}</span>
                  <V4Badge tone={stepTone(step.status)}>{step.status}</V4Badge>
                </div>
                <p className="mt-0.5 text-[11px] text-(--qs-text-3)">{step.detail}</p>
              </li>
            ))}
          </ul>

          {snapshot.actions.length > 0 ? (
            <ul className="space-y-2">
              {snapshot.actions.map((action) => (
                <li key={action.id} className="rounded border border-white/10 bg-black/20 p-2 text-xs">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-medium text-(--qs-text)">{action.label}</span>
                    {action.href ? (
                      <Link href={action.href} className="text-cyan hover:underline">
                        Open
                      </Link>
                    ) : null}
                  </div>
                  <p className="mt-1 text-(--qs-text-3)">{action.detail}</p>
                </li>
              ))}
            </ul>
          ) : null}

          <Link href="/factory" className="text-xs text-cyan hover:underline">
            Public factory blueprint →
          </Link>
        </>
      ) : null}
    </div>
  );
}

export const ExecutionStudioMicroSaasFactoryPanel = memo(ExecutionStudioMicroSaasFactoryPanelInner);
