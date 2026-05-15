import { HivePageHeader } from "@/components/hive/hive-page-header";
import { SectionNavGrid } from "@/components/hive/section-nav-grid";
import { ADVANCED_MONITORING_ENABLED } from "@/lib/feature-flags";

export default function OverviewPage(): JSX.Element {
  return (
    <div className="space-y-8">
      <HivePageHeader
        title="Overview"
        subtitle="High-signal cockpit entrypoint. Jump to live swarm status, monitoring, costs, and system readiness."
      />
      <SectionNavGrid
        items={[
          { href: "/", title: "Dashboard", description: "Live colony board, quick mission context, and active bees." },
          { href: "/swarms", title: "Swarms", description: "Inspect swarm composition and cross-lane behavior." },
          { href: "/costs", title: "Costs", description: "Track LLM spend, caps, and efficiency trends." },
          ...(ADVANCED_MONITORING_ENABLED
            ? [{ href: "/monitoring", title: "Monitoring", description: "Host pressure, queue depth, and telemetry diagnostics." }]
            : []),
        ]}
      />
    </div>
  );
}
