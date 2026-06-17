"use client";

import Link from "next/link";
import { Loader2Icon, PackageIcon, RocketIcon, StoreIcon } from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { COCKPIT_POLL_COLONY_TELEMETRY_MS } from "@/lib/cockpit-poll-profile";
import { DASHBOARD_BOOT_STAGGER_MS } from "@/lib/dashboard-boot-stagger";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";
import type { FactoryLaunchPayload, FactoryLaunchPreparePayload } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

/** REV4 — Factory Queue → Launch funnel for first Gumroad sellable harness. */
export function FactoryLaunchWidget({ eager = false }: { eager?: boolean }): JSX.Element {
  const [payload, setPayload] = useState<FactoryLaunchPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [prepareBusy, setPrepareBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const body = await hiveGet<FactoryLaunchPayload>("dashboard/factory-launch");
      setPayload(body);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Factory launch telemetry unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  const prepareBatch = useCallback(async () => {
    setPrepareBusy(true);
    try {
      const result = await hivePostJson<FactoryLaunchPreparePayload>(
        "dashboard/factory-launch/prepare?limit=3",
        {},
      );
      if (result.ok && result.exported_count > 0) {
        toast.success(result.message ?? `Exported ${result.exported_count} harness pack(s).`);
      } else {
        toast.message(result.message ?? "No sellable skills ready for export yet.");
      }
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Launch batch export failed.");
    } finally {
      setPrepareBusy(false);
    }
  }, [load]);

  useIntervalWhenVisible(() => void load(), COCKPIT_POLL_COLONY_TELEMETRY_MS, {
    initialDelayMs: eager ? 0 : DASHBOARD_BOOT_STAGGER_MS.factoryLaunch,
  });

  const funnelReady = payload?.funnel_ready ?? false;
  const gumroadReady = payload?.gumroad_ready ?? false;

  return (
    <div data-testid="factory-launch-widget">
      <V4Card className="v4-card-interactive">
        <V4CardHeader
          title="Factory launch"
          description="Research → build → approve → Gumroad queue"
          actions={
            payload?.enabled ? (
              <V4Badge tone={funnelReady && gumroadReady ? "ok" : "warn"}>
                <RocketIcon className="mr-1 inline h-3 w-3" aria-hidden />
                {funnelReady ? (gumroadReady ? "sellable" : "queue ready") : "building"}
              </V4Badge>
            ) : null
          }
        />

        {loading ? (
          <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
            <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading launch funnel…
          </p>
        ) : null}

        {err ? <p className="text-sm text-(--qs-red)">{err}</p> : null}

        {!loading && !err && payload?.enabled ? (
          <>
            <div className="mb-3 flex flex-wrap gap-3 text-xs text-(--qs-text-2)">
              <span>
                Sellable{" "}
                <span className="font-mono text-pollen">{payload.sellable_count}</span>
              </span>
              <span>
                Launch queue{" "}
                <span className="font-mono text-cyan">{payload.launch_queue_count}</span>
              </span>
              <span>
                Building{" "}
                <span className="font-mono">{payload.building_count}</span>
              </span>
              <span className={cn(!gumroadReady && payload.launch_queue_count > 0 && "text-(--qs-magenta)")}>
                Gumroad{" "}
                <span className="font-mono">{gumroadReady ? "ready" : "setup"}</span>
              </span>
            </div>

            {payload.top_launch_titles.length > 0 ? (
              <ul className="mb-3 space-y-1 text-xs text-(--qs-text-2)">
                {payload.top_launch_titles.map((title) => (
                  <li key={title} className="flex items-center gap-1.5">
                    <StoreIcon className="h-3 w-3 shrink-0 text-pollen" aria-hidden />
                    <span className="truncate">{title}</span>
                  </li>
                ))}
              </ul>
            ) : null}

            <p className="mb-3 text-sm text-(--qs-text-3)">{payload.operator_hint}</p>

            <div className="flex flex-wrap items-center gap-2">
              {payload.prepare_available ? (
                <button
                  type="button"
                  className="qs-btn qs-btn--primary qs-btn--sm min-h-[44px] gap-1"
                  disabled={prepareBusy}
                  onClick={() => void prepareBatch()}
                  data-testid="factory-launch-prepare-btn"
                >
                  {prepareBusy ? (
                    <Loader2Icon className="size-3.5 animate-spin" aria-hidden />
                  ) : (
                    <PackageIcon className="size-3.5" aria-hidden />
                  )}
                  Prepare Gumroad batch
                </button>
              ) : null}
              <Link
                href={payload.launch_href}
                className={cn(
                  "qs-btn qs-btn--sm min-h-[44px] gap-1",
                  payload.prepare_available
                    ? "qs-btn--ghost border border-(--qs-border)/50"
                    : "qs-btn--primary",
                )}
              >
                Open launch queue
                <RocketIcon className="size-3.5" aria-hidden />
              </Link>
              <Link
                href={payload.factory_href}
                className="qs-btn qs-btn--ghost qs-btn--sm min-h-[44px] border border-(--qs-border)/50"
              >
                Skill Factory
              </Link>
              <HiveRefreshButton onClick={() => void load()} label="Refresh launch funnel" />
            </div>
          </>
        ) : null}

        {!loading && !err && payload && !payload.enabled ? (
          <p className="text-sm text-(--qs-text-3)">{payload.operator_hint || "Factory launch widget disabled."}</p>
        ) : null}
      </V4Card>
    </div>
  );
}
