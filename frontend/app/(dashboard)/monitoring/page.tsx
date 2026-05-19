"use client";

import { HivePageHeader } from "@/components/hive/hive-page-header";
import { MonitoringDashboard } from "@/components/monitoring/monitoring-dashboard";
import { V4PageCanvas } from "@/components/ui/v4";
import { ADVANCED_MONITORING_ENABLED } from "@/lib/feature-flags";

export default function MonitoringPage() {
  if (!ADVANCED_MONITORING_ENABLED) {
    return (
      <V4PageCanvas>
        <div className="rounded-2xl border border-cyan/20 bg-black/30 p-5">
          <p className="font-[family-name:var(--font-poppins)] text-sm text-zinc-300">
            Advanced monitoring mode is disabled. Enable <code>NEXT_PUBLIC_ADVANCED_MONITORING_ENABLED=true</code> to view
            this cockpit section.
          </p>
        </div>
      </V4PageCanvas>
    );
  }

  return (
    <V4PageCanvas>
      <HivePageHeader
        title="Monitoring"
        subtitle="Enterprise-only observability cockpit: scaling pressure, costs, alerts, and tenant-aware operator health."
      />
      <MonitoringDashboard />
    </V4PageCanvas>
  );
}
