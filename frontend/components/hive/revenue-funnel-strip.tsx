"use client";

import Link from "next/link";
import { CheckCircle2Icon, CircleIcon, Loader2Icon, RocketIcon } from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { COCKPIT_POLL_COLONY_TELEMETRY_MS } from "@/lib/cockpit-poll-profile";
import { DASHBOARD_BOOT_STAGGER_MS } from "@/lib/dashboard-boot-stagger";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";
import type {
  CatalogWaveSeedBatchPayload,
  FactoryLaunchFullFunnelPayload,
  FactoryLaunchLaunchAndVerifyPayload,
  FactoryLaunchPreparePayload,
  RevenueFunnelPayload,
} from "@/lib/hive-types";
import { cn } from "@/lib/utils";

/** MK10 — Unified MK6 catalog scale + Gumroad launch funnel strip. */
export function RevenueFunnelStrip({ eager = false }: { eager?: boolean }): JSX.Element {
  const [payload, setPayload] = useState<RevenueFunnelPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const body = await hiveGet<RevenueFunnelPayload>("dashboard/revenue-funnel");
      setPayload(body);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Revenue funnel telemetry unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  const runPrimaryAction = useCallback(async () => {
    const action = payload?.primary_action;
    if (!action?.post_path) {
      return;
    }
    setActionBusy(true);
    try {
      if (action.id === "launch_and_verify") {
        const result = await hivePostJson<FactoryLaunchLaunchAndVerifyPayload>(
          `${action.post_path}?limit=3`,
          {},
        );
        if (result.ok) {
          toast.success(result.message ?? "Launch & verify complete.");
        } else {
          toast.message(result.message ?? "Launch & verify incomplete.");
        }
      } else if (action.id === "full_funnel") {
        const result = await hivePostJson<FactoryLaunchFullFunnelPayload>(
          `${action.post_path}?limit=3`,
          {},
        );
        toast.message(result.message ?? (result.ok ? "Full funnel complete." : "Full funnel incomplete."));
      } else if (action.id === "prepare") {
        const result = await hivePostJson<FactoryLaunchPreparePayload>(
          `${action.post_path}?limit=3`,
          {},
        );
        toast.message(result.message ?? (result.ok ? "Batch prepared." : "Prepare batch skipped."));
      } else if (action.id === "factory_seeds") {
        const result = await hivePostJson<CatalogWaveSeedBatchPayload>(
          `${action.post_path}?limit=3`,
          {},
        );
        if (result.ok) {
          toast.success(result.message);
        } else {
          toast.message(result.message);
        }
      }
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Revenue funnel action failed.");
    } finally {
      setActionBusy(false);
    }
  }, [load, payload?.primary_action]);

  useIntervalWhenVisible(() => void load(), COCKPIT_POLL_COLONY_TELEMETRY_MS, {
    initialDelayMs: eager ? 0 : DASHBOARD_BOOT_STAGGER_MS.revenueFunnel,
  });

  const loopReady = payload?.revenue_loop_ready ?? false;
  const progressPct =
    payload && payload.mk6_target > 0
      ? Math.min(100, Math.round((100 * payload.scorecard_clean_count) / payload.mk6_target))
      : 0;

  return (
    <div id="revenue-funnel" data-testid="revenue-funnel-strip">
      <V4Card className="v4-card-interactive border-pollen/20">
        <V4CardHeader
          title="Revenue funnel"
          description="MK6 catalog → sellable harness → Gumroad live → closed loop"
          actions={
            payload?.enabled ? (
              <V4Badge tone={payload.funnel_complete || loopReady ? "ok" : "warn"}>
                <RocketIcon className="mr-1 inline h-3 w-3" aria-hidden />
                {payload.funnel_complete ? "complete" : loopReady ? "loop closed" : "in progress"}
              </V4Badge>
            ) : null
          }
        />

        {loading ? (
          <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
            <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading revenue funnel…
          </p>
        ) : null}

        {err ? <p className="text-sm text-(--qs-red)">{err}</p> : null}

        {!loading && !err && payload?.enabled ? (
          <>
            <div className="mb-3 flex flex-wrap gap-3 text-xs text-(--qs-text-2)">
              <span>
                MK6{" "}
                <span className="font-mono text-pollen">
                  {payload.scorecard_clean_count}/{payload.mk6_target}
                </span>
              </span>
              <span>
                Sellable <span className="font-mono text-cyan">{payload.sellable_count}</span>
              </span>
              <span>
                Live <span className="font-mono text-(--qs-green)">{payload.published_gumroad_count}</span>
              </span>
              <span>
                Gap <span className="font-mono">{payload.gap_to_mk6}</span>
              </span>
            </div>

            <div
              className="mb-3 h-1.5 overflow-hidden rounded-full bg-(--qs-border)/40"
              role="progressbar"
              aria-valuenow={progressPct}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="MK6 catalog progress"
            >
              <div
                className="h-full rounded-full bg-pollen transition-all"
                style={{ width: `${progressPct}%` }}
              />
            </div>

            <ul className="mb-3 grid gap-1.5 sm:grid-cols-2">
              {payload.steps.map((step) => (
                <li
                  key={step.id}
                  className={cn(
                    "flex items-start gap-2 rounded-md border border-(--qs-border)/40 px-2 py-1.5 text-xs",
                    step.done && "border-(--qs-green)/30 bg-(--qs-green)/5",
                  )}
                >
                  {step.done ? (
                    <CheckCircle2Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-(--qs-green)" aria-hidden />
                  ) : (
                    <CircleIcon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-(--qs-text-3)" aria-hidden />
                  )}
                  <span>
                    <span className="font-medium text-(--qs-text-1)">{step.label}</span>
                    <span className="block text-(--qs-text-3)">{step.detail}</span>
                  </span>
                </li>
              ))}
            </ul>

            <div className="flex flex-wrap items-center gap-2">
              {payload.primary_action && !payload.funnel_complete ? (
                payload.primary_action.post_path ? (
                  <button
                    type="button"
                    className="qs-btn qs-btn--primary qs-btn--sm min-h-[44px] gap-1"
                    disabled={actionBusy}
                    onClick={() => void runPrimaryAction()}
                  >
                    {actionBusy ? (
                      <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden />
                    ) : (
                      <RocketIcon className="h-4 w-4" aria-hidden />
                    )}
                    {payload.primary_action.label}
                  </button>
                ) : (
                  <Link
                    href={payload.primary_action.href ?? payload.factory_href}
                    className="qs-btn qs-btn--primary qs-btn--sm min-h-[44px] gap-1"
                  >
                    <RocketIcon className="h-4 w-4" aria-hidden />
                    {payload.primary_action.label}
                  </Link>
                )
              ) : null}
              <Link href={payload.factory_href} className="qs-btn qs-btn--ghost qs-btn--sm min-h-[44px]">
                Skill Factory
              </Link>
              <Link
                href={payload.catalog_href}
                className="qs-btn qs-btn--ghost qs-btn--sm min-h-[44px]"
                target="_blank"
                rel="noopener noreferrer"
              >
                Catalog
              </Link>
              <HiveRefreshButton onClick={() => void load()} label="Refresh funnel" />
            </div>

            {payload.operator_hint ? (
              <p className="mt-3 text-xs text-(--qs-text-3)">{payload.operator_hint}</p>
            ) : null}
          </>
        ) : null}
      </V4Card>
    </div>
  );
}
