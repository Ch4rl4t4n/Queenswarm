"use client";

import dynamic from "next/dynamic";
import Link from "next/link";

import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HivePanelSectionSkeleton } from "@/components/hive/hive-panel-section-skeleton";
import { TASKS_HUB_PATH } from "@/lib/execution-lane-routes";
import { ADVANCED_MONITORING_ENABLED } from "@/lib/feature-flags";

const MonitoringDashboard = dynamic(
  () => import("@/components/monitoring/monitoring-dashboard").then((mod) => ({ default: mod.MonitoringDashboard })),
  { loading: () => <HivePanelSectionSkeleton label="Loading monitoring dashboard…" /> },
);

const MONITORING_SUBTITLE =
  "Enterprise observability cockpit — scaling pressure, costs, alerts, and tenant-aware operator health.";

/** Monitoring route — HivePageShell wrapper for observability dashboard. */
export function MonitoringPageClient(): JSX.Element {
  if (!ADVANCED_MONITORING_ENABLED) {
    return (
      <HivePageShell title="Monitoring" subtitle={MONITORING_SUBTITLE} hintKey="monitoring">
        <div className="rounded-2xl border border-cyan/20 bg-black/30 p-5">
          <p className="font-[family-name:var(--font-poppins)] text-sm text-zinc-300">
            Advanced monitoring mode is disabled. Enable{" "}
            <code className="text-(--qs-cyan)">NEXT_PUBLIC_ADVANCED_MONITORING_ENABLED=true</code> to view this cockpit
            section.
          </p>
        </div>
      </HivePageShell>
    );
  }

  return (
    <HivePageShell
      title="Monitoring"
      subtitle={MONITORING_SUBTITLE}
      hintKey="monitoring"
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link href="/agentic-os" className="qs-btn qs-btn--ghost qs-btn--sm">
            Agentic OS
          </Link>
          <Link href={TASKS_HUB_PATH} className="qs-btn qs-btn--ghost qs-btn--sm">
            Tasks hub
          </Link>
        </div>
      }
    >
      <MonitoringDashboard />
    </HivePageShell>
  );
}
