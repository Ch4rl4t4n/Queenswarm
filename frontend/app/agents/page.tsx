import { AgentHexCard } from "@/components/hive/agent-hex-card";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { AgentRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

export default async function AgentsPage() {
  const rows = await hiveServerRawJson<AgentRow[]>("/agents?limit=120");

  if (!rows) {
    return <p className="text-danger font-[family-name:var(--font-jetbrains-mono)] text-sm">Could not sync agents ledger.</p>;
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-[family-name:var(--font-space-grotesk)] text-3xl font-semibold text-pollen">
          swarm bees
        </h1>
        <p className="mt-2 max-w-2xl font-[family-name:var(--font-jetbrains-mono)] text-sm text-cyan">
          Idle / busy / simulator states glow with pollen-weighted halo — imitate top performers straight from hex cells.
        </p>
      </header>
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5">
        {rows.map((agent) => (
          <AgentHexCard key={agent.id} agent={agent} />
        ))}
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground font-[family-name:var(--font-jetbrains-mono)]">
          No bees yet — bootstrap with backend/scripts/hive_seed.py inside the API container.
        </p>
      ) : null}
    </div>
  );
}
