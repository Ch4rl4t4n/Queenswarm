"use client";

import Link from "next/link";
import { Loader2Icon, PackageIcon, RefreshCwIcon, RocketIcon, ShieldCheckIcon, StoreIcon, TestTubeDiagonalIcon } from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { COCKPIT_POLL_COLONY_TELEMETRY_MS } from "@/lib/cockpit-poll-profile";
import { DASHBOARD_BOOT_STAGGER_MS } from "@/lib/dashboard-boot-stagger";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";
import type {
  FactoryLaunchCatalogSyncPayload,
  FactoryLaunchGumroadDraftPayload,
  FactoryLaunchGumroadPublishPayload,
  FactoryLaunchPayload,
  FactoryLaunchPreparePayload,
  FactoryLaunchPurchaseSmokePayload,
  FactoryLaunchRevenueSmokePayload,
} from "@/lib/hive-types";
import { cn } from "@/lib/utils";

/** REV4 — Factory Queue → Launch funnel for first Gumroad sellable harness. */
export function FactoryLaunchWidget({ eager = false }: { eager?: boolean }): JSX.Element {
  const [payload, setPayload] = useState<FactoryLaunchPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [prepareBusy, setPrepareBusy] = useState(false);
  const [draftBusy, setDraftBusy] = useState(false);
  const [publishBusy, setPublishBusy] = useState(false);
  const [smokeBusy, setSmokeBusy] = useState(false);
  const [catalogSyncBusy, setCatalogSyncBusy] = useState(false);
  const [purchaseSmokeBusy, setPurchaseSmokeBusy] = useState(false);

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

  const createGumroadDrafts = useCallback(async () => {
    setDraftBusy(true);
    try {
      const result = await hivePostJson<FactoryLaunchGumroadDraftPayload>(
        "dashboard/factory-launch/gumroad-draft?limit=3",
        {},
      );
      if (result.ok && result.drafted_count > 0) {
        toast.success(result.message ?? `Created ${result.drafted_count} Gumroad draft(s).`);
      } else {
        toast.message(result.message ?? "No Gumroad drafts created.");
      }
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Gumroad draft batch failed.");
    } finally {
      setDraftBusy(false);
    }
  }, [load]);

  const publishGumroadListings = useCallback(async () => {
    setPublishBusy(true);
    try {
      const result = await hivePostJson<FactoryLaunchGumroadPublishPayload>(
        "dashboard/factory-launch/gumroad-publish?limit=3",
        {},
      );
      if (result.ok && result.published_count > 0) {
        toast.success(result.message ?? `Published ${result.published_count} Gumroad listing(s).`);
      } else {
        toast.message(result.message ?? "No Gumroad listings published.");
      }
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Gumroad publish batch failed.");
    } finally {
      setPublishBusy(false);
    }
  }, [load]);

  const verifyRevenueLoop = useCallback(async () => {
    setSmokeBusy(true);
    try {
      const result = await hivePostJson<FactoryLaunchRevenueSmokePayload>(
        "dashboard/factory-launch/revenue-smoke",
        {},
      );
      if (result.ok) {
        toast.success(result.message ?? "Revenue loop verified.");
      } else {
        const failing = result.checks.filter((row) => !row.ok).map((row) => row.label);
        toast.message(
          failing.length > 0
            ? `${result.message ?? "Revenue loop incomplete."} Missing: ${failing.join(", ")}.`
            : (result.message ?? "Revenue loop incomplete."),
        );
      }
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Revenue loop smoke failed.");
    } finally {
      setSmokeBusy(false);
    }
  }, [load]);

  const syncSkillsCatalog = useCallback(async () => {
    setCatalogSyncBusy(true);
    try {
      const result = await hivePostJson<FactoryLaunchCatalogSyncPayload>(
        "dashboard/factory-launch/catalog-sync",
        {},
      );
      if (result.ok && result.synced_count > 0) {
        toast.success(result.message ?? `Synced ${result.synced_count} catalog URL(s).`);
      } else {
        toast.message(result.message ?? "Catalog sync completed with no new URLs.");
      }
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Catalog sync failed.");
    } finally {
      setCatalogSyncBusy(false);
    }
  }, [load]);

  const simulatePurchase = useCallback(async () => {
    setPurchaseSmokeBusy(true);
    try {
      const result = await hivePostJson<FactoryLaunchPurchaseSmokePayload>(
        "dashboard/factory-launch/purchase-smoke",
        {},
      );
      if (result.ok) {
        toast.success(result.message ?? "Purchase smoke completed.");
      } else {
        toast.message(result.message ?? "Purchase smoke did not complete.");
      }
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Purchase smoke failed.");
    } finally {
      setPurchaseSmokeBusy(false);
    }
  }, [load]);

  useIntervalWhenVisible(() => void load(), COCKPIT_POLL_COLONY_TELEMETRY_MS, {
    initialDelayMs: eager ? 0 : DASHBOARD_BOOT_STAGGER_MS.factoryLaunch,
  });

  const funnelReady = payload?.funnel_ready ?? false;
  const gumroadReady = payload?.gumroad_ready ?? false;
  const revenueLoopReady = payload?.revenue_loop_ready ?? false;

  return (
    <div data-testid="factory-launch-widget">
      <V4Card className="v4-card-interactive">
        <V4CardHeader
          title="Factory launch"
          description="Research → build → approve → Gumroad queue"
          actions={
            payload?.enabled ? (
              <V4Badge tone={revenueLoopReady ? "ok" : funnelReady && gumroadReady ? "ok" : "warn"}>
                <RocketIcon className="mr-1 inline h-3 w-3" aria-hidden />
                {revenueLoopReady ? "loop closed" : funnelReady ? (gumroadReady ? "sellable" : "queue ready") : "building"}
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
              <span>
                Pending drafts{" "}
                <span className="font-mono">{payload.pending_gumroad_draft_count}</span>
              </span>
              <span>
                Pending publish{" "}
                <span className="font-mono text-(--qs-green)">{payload.pending_gumroad_publish_count}</span>
              </span>
              <span>
                Live{" "}
                <span className="font-mono text-(--qs-green)">{payload.published_gumroad_count}</span>
              </span>
              <span>
                Webhook{" "}
                <span className="font-mono">{payload.purchase_webhook_ready ? "ready" : "setup"}</span>
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
              {payload.purchase_smoke_available ? (
                <button
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--sm min-h-[44px] gap-1 border border-(--qs-border)/50"
                  disabled={purchaseSmokeBusy}
                  onClick={() => void simulatePurchase()}
                  data-testid="factory-launch-purchase-smoke-btn"
                >
                  {purchaseSmokeBusy ? (
                    <Loader2Icon className="size-3.5 animate-spin" aria-hidden />
                  ) : (
                    <TestTubeDiagonalIcon className="size-3.5" aria-hidden />
                  )}
                  Simulate purchase
                </button>
              ) : null}
              {payload.catalog_sync_available ? (
                <button
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--sm min-h-[44px] gap-1 border border-(--qs-border)/50"
                  disabled={catalogSyncBusy}
                  onClick={() => void syncSkillsCatalog()}
                  data-testid="factory-launch-catalog-sync-btn"
                >
                  {catalogSyncBusy ? (
                    <Loader2Icon className="size-3.5 animate-spin" aria-hidden />
                  ) : (
                    <RefreshCwIcon className="size-3.5" aria-hidden />
                  )}
                  Sync skills catalog
                </button>
              ) : null}
              {payload.revenue_smoke_available ? (
                <button
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--sm min-h-[44px] gap-1 border border-(--qs-border)/50"
                  disabled={smokeBusy}
                  onClick={() => void verifyRevenueLoop()}
                  data-testid="factory-launch-revenue-smoke-btn"
                >
                  {smokeBusy ? (
                    <Loader2Icon className="size-3.5 animate-spin" aria-hidden />
                  ) : (
                    <ShieldCheckIcon className="size-3.5" aria-hidden />
                  )}
                  Verify revenue loop
                </button>
              ) : null}
              {payload.gumroad_auto_publish_available ? (
                <button
                  type="button"
                  className="qs-btn qs-btn--primary qs-btn--sm min-h-[44px] gap-1"
                  disabled={publishBusy}
                  onClick={() => void publishGumroadListings()}
                  data-testid="factory-launch-gumroad-publish-btn"
                >
                  {publishBusy ? (
                    <Loader2Icon className="size-3.5 animate-spin" aria-hidden />
                  ) : (
                    <RocketIcon className="size-3.5" aria-hidden />
                  )}
                  Publish Gumroad listings
                </button>
              ) : null}
              {payload.gumroad_auto_draft_available ? (
                <button
                  type="button"
                  className="qs-btn qs-btn--primary qs-btn--sm min-h-[44px] gap-1"
                  disabled={draftBusy}
                  onClick={() => void createGumroadDrafts()}
                  data-testid="factory-launch-gumroad-draft-btn"
                >
                  {draftBusy ? (
                    <Loader2Icon className="size-3.5 animate-spin" aria-hidden />
                  ) : (
                    <StoreIcon className="size-3.5" aria-hidden />
                  )}
                  Create Gumroad drafts
                </button>
              ) : null}
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
              <Link
                href={payload.catalog_href}
                className="qs-btn qs-btn--ghost qs-btn--sm min-h-[44px] border border-(--qs-border)/50"
              >
                Skills catalog
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
