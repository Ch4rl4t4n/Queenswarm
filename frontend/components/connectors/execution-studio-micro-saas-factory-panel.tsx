"use client";

import { Factory } from "lucide-react";
import Link from "next/link";
import { memo, useCallback, useEffect, useState, type ReactNode } from "react";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { FACTORY_BLUEPRINT_PATH, FACTORY_CROSS_LINK_LABELS } from "@/lib/factory-content-factory-routes";
import { cn } from "@/lib/utils";

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
  deploy_domain: string;
  steps: MicroSaasStep[];
  actions: MicroSaasAction[];
}

export interface ExecutionStudioMicroSaasFactoryPanelProps {
  onError: (message: string | null) => void;
  /** Hide spawn row when the page header already exposes the same CTA (e.g. `/factory`). */
  hideSpawnAction?: boolean;
}

function stepTone(status: string): "ok" | "warn" | "info" {
  if (status === "done") return "ok";
  if (status === "pending") return "info";
  return "warn";
}

function MicroSaasStatusRow({
  title,
  detail,
  status,
  className,
  emphasis = false,
}: {
  title: string;
  detail: string;
  status: ReactNode;
  className?: string;
  emphasis?: boolean;
}) {
  return (
    <li
      className={cn(
        "grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-0.5 rounded bg-black/20 px-2 py-1.5",
        className,
      )}
    >
      <span
        className={cn(
          "col-start-1 row-start-1 min-w-0 text-(--qs-text)",
          emphasis && "font-medium",
        )}
      >
        {title}
      </span>
      <div className="col-start-2 row-start-1 shrink-0 self-start justify-self-end pt-px">{status}</div>
      <p className="col-start-1 row-start-2 min-w-0 text-[11px] leading-snug text-(--qs-text-3)">{detail}</p>
    </li>
  );
}

function ExecutionStudioMicroSaasFactoryPanelInner({
  onError,
  hideSpawnAction = false,
}: ExecutionStudioMicroSaasFactoryPanelProps) {
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
        <HiveRefreshButton busy={loading} onClick={() => void load()} />
      </div>

      {loading && !snapshot ? (
        <p className="text-xs text-(--qs-text-3)">Loading factory checklist…</p>
      ) : snapshot ? (
        <>
          <div className="flex flex-wrap gap-2 text-xs">
            <V4Badge tone="info">{snapshot.product_name}</V4Badge>
            <V4Badge tone={snapshot.progress_pct >= 75 ? "ok" : "warn"}>{snapshot.progress_pct}% ready</V4Badge>
          </div>

          <ul className="space-y-1 text-xs">
            {snapshot.steps.map((step) => (
              <MicroSaasStatusRow
                key={step.id}
                title={step.label}
                detail={step.detail}
                status={<V4Badge tone={stepTone(step.status)}>{step.status}</V4Badge>}
              />
            ))}
            {snapshot.actions
              .filter((action) => !(hideSpawnAction && action.id === "spawn_factory"))
              .map((action) => (
                <MicroSaasStatusRow
                  key={action.id}
                  title={action.label}
                  detail={action.detail}
                  emphasis
                  className="border border-white/10"
                  status={
                    action.href ? (
                      <Link href={action.href} className="qs-btn qs-btn--ghost qs-btn--sm shrink-0">
                        Open
                      </Link>
                    ) : null
                  }
                />
              ))}
          </ul>

          <div className="flex justify-end pt-1">
            {!hideSpawnAction ? (
              <Link href={FACTORY_BLUEPRINT_PATH} className="qs-btn qs-btn--primary qs-btn--sm shrink-0">
                {FACTORY_CROSS_LINK_LABELS.toBlueprint}
              </Link>
            ) : null}
          </div>
        </>
      ) : null}
    </div>
  );
}

export const ExecutionStudioMicroSaasFactoryPanel = memo(ExecutionStudioMicroSaasFactoryPanelInner);
