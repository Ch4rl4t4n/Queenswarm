import { HivePageHeader } from "@/components/hive/hive-page-header";
import { SectionNavGrid } from "@/components/hive/section-nav-grid";
import { SIMULATIONS_ENABLED } from "@/lib/feature-flags";

export default function ExecutionPage(): JSX.Element {
  return (
    <div className="space-y-8">
      <HivePageHeader
        title="Execution"
        subtitle="Mission delivery lane. Plan, queue, run, and inspect tasks/workflows/jobs/routines from one section."
      />
      <SectionNavGrid
        items={[
          { href: "/tasks/new", title: "New task", description: "Compose and dispatch a mission into the hive queue." },
          { href: "/tasks", title: "Tasks", description: "Backlog lifecycle, statuses, and execution history." },
          { href: "/workflows", title: "Workflows", description: "Visual DAG management with pause/cancel controls." },
          { href: "/jobs", title: "Async jobs", description: "Inspect Celery-backed execution jobs and retries." },
          { href: "/agents", title: "Routines & Supervisor", description: "Use supervisor sessions and recurring routines." },
          ...(SIMULATIONS_ENABLED
            ? [{ href: "/simulations", title: "Simulations", description: "Verified simulation ledger and compliance snapshots." }]
            : []),
        ]}
      />
    </div>
  );
}
