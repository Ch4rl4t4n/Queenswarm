"use client";

import { HivePageHeader } from "@/components/hive/hive-page-header";
import { MonitoringDashboard } from "@/components/monitoring/monitoring-dashboard";
import { ADVANCED_MONITORING_ENABLED } from "@/lib/feature-flags";

export default function MonitoringPage() {
  if (!ADVANCED_MONITORING_ENABLED) {
    return (
      <div className="rounded-2xl border border-cyan/20 bg-black/30 p-5">
        <p className="font-[family-name:var(--font-poppins)] text-sm text-zinc-300">
          Advanced monitoring mode is disabled. Enable <code>NEXT_PUBLIC_ADVANCED_MONITORING_ENABLED=true</code> to view
          this cockpit section.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <HivePageHeader
        title="Monitoring"
        subtitle="Host pressure, Docker fan-out, hive throughput, and 24h LLM burn — live cockpit."
      />
      <MonitoringDashboard />
    </div>
  );
}
