"use client";

import Link from "next/link";
import { BarChart3Icon, Loader2Icon } from "lucide-react";
import { useCallback, useState } from "react";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { COCKPIT_POLL_COLONY_TELEMETRY_MS } from "@/lib/cockpit-poll-profile";
import { DASHBOARD_BOOT_STAGGER_MS } from "@/lib/dashboard-boot-stagger";
import { HiveApiError, hiveGet } from "@/lib/api";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";
import type { CatalogWavePayload } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

/** MK9 — MK6 catalog wave progress toward 50+ scorecard-clean listings. */
export function CatalogWaveWidget({ eager = false }: { eager?: boolean }): JSX.Element {
  const [payload, setPayload] = useState<CatalogWavePayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const body = await hiveGet<CatalogWavePayload>("dashboard/catalog-wave");
      setPayload(body);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Catalog wave telemetry unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useIntervalWhenVisible(() => void load(), COCKPIT_POLL_COLONY_TELEMETRY_MS, {
    initialDelayMs: eager ? 0 : DASHBOARD_BOOT_STAGGER_MS.catalogWave,
  });

  const progressPct =
    payload && payload.mk6_target > 0
      ? Math.min(100, Math.round((100 * payload.scorecard_clean_count) / payload.mk6_target))
      : 0;

  return (
    <div data-testid="catalog-wave-widget">
      <V4Card className="v4-card-interactive">
        <V4CardHeader
          title="Catalog wave"
          description="MK6 scale — scorecard-clean listings → letagentscook.org"
          actions={
            payload?.enabled ? (
              <V4Badge tone={payload.wave_complete ? "ok" : "warn"}>
                <BarChart3Icon className="mr-1 inline h-3 w-3" aria-hidden />
                {payload.wave_complete ? "MK6 met" : payload.current_wave.replace("_", " ")}
              </V4Badge>
            ) : null
          }
        />

        {loading ? (
          <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
            <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading catalog wave…
          </p>
        ) : null}

        {err ? <p className="text-sm text-(--qs-red)">{err}</p> : null}

        {!loading && !err && payload?.enabled ? (
          <>
            <div className="mb-3 flex flex-wrap gap-3 text-xs text-(--qs-text-2)">
              <span>
                Scorecard clean{" "}
                <span className="font-mono text-pollen">
                  {payload.scorecard_clean_count}/{payload.mk6_target}
                </span>
              </span>
              <span>
                Catalog deduped{" "}
                <span className="font-mono text-cyan">{payload.catalog_deduped_count}</span>
              </span>
              <span>
                Gap next wave{" "}
                <span className="font-mono">{payload.gap_to_next_wave}</span>
              </span>
              <span>
                Pending seeds{" "}
                <span className="font-mono text-(--qs-green)">{payload.seed_pending_count}</span>
              </span>
            </div>

            <div
              className="mb-3 h-2 overflow-hidden rounded-full bg-(--qs-border)/30"
              role="progressbar"
              aria-valuenow={progressPct}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="MK6 catalog wave progress"
            >
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  payload.wave_complete ? "bg-(--qs-green)" : "bg-pollen",
                )}
                style={{ width: `${progressPct}%` }}
              />
            </div>

            {payload.pending_seeds_preview.length > 0 ? (
              <ul className="mb-3 space-y-1 text-xs text-(--qs-text-2)">
                {payload.pending_seeds_preview.map((seed) => (
                  <li key={seed} className="truncate font-mono">
                    {seed}
                  </li>
                ))}
              </ul>
            ) : null}

            <p className="mb-3 text-sm text-(--qs-text-3)">{payload.operator_hint}</p>

            <div className="flex flex-wrap items-center gap-2">
              <Link
                href={payload.factory_href}
                className="qs-btn qs-btn--primary qs-btn--sm min-h-[44px]"
                data-testid="catalog-wave-factory-link"
              >
                Open Skill Factory
              </Link>
              <a
                href={payload.catalog_href}
                className="qs-btn qs-btn--ghost qs-btn--sm min-h-[44px] border border-(--qs-border)/50"
                target="_blank"
                rel="noopener noreferrer"
                data-testid="catalog-wave-catalog-link"
              >
                View catalog
              </a>
              <HiveRefreshButton onClick={() => void load()} label="Refresh wave" />
            </div>
          </>
        ) : null}
      </V4Card>
    </div>
  );
}
