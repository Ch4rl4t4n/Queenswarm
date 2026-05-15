import { HivePageHeader } from "@/components/hive/hive-page-header";
import { SectionNavGrid } from "@/components/hive/section-nav-grid";
import { LEADERBOARD_ENABLED, RECIPES_ENABLED } from "@/lib/feature-flags";

export default function KnowledgePage(): JSX.Element {
  return (
    <div className="space-y-8">
      <HivePageHeader
        title="Knowledge"
        subtitle="Shared memory and outcomes. Consolidated access to HiveMind, outputs, learning, and optional recipe intelligence."
      />
      <SectionNavGrid
        items={[
          { href: "/hive-mind", title: "HiveMind", description: "Explore vector + graph memory context and knowledge links." },
          { href: "/outputs", title: "Outputs", description: "Archived deliverables with semantic search and lineage context." },
          { href: "/learning", title: "Learning", description: "Pollen, imitation, and reflection telemetry for quality loops." },
          ...(RECIPES_ENABLED
            ? [{ href: "/recipes", title: "Recipes", description: "Reusable workflow catalog for verified execution patterns." }]
            : []),
          ...(LEADERBOARD_ENABLED
            ? [{ href: "/leaderboard", title: "Leaderboard", description: "Top performers and quality progression indicators." }]
            : []),
        ]}
      />
    </div>
  );
}
