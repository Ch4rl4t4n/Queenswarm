import Link from "next/link";

import { AgentsPageRoster } from "@/components/hive/agents-page-roster";
import { AgentsSessionsPanel } from "@/components/hive/agents-sessions-panel";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import { HierarchyPageConsole } from "@/components/hive/hierarchy-page-console";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { AgentRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

export default async function AgentsPage() {
  const rows = await hiveServerRawJson<AgentRow[]>("/agents?limit=120");

  if (!rows) {
    return <p className="font-(family-name:--font-poppins) text-sm text-danger">Could not sync agents ledger.</p>;
  }

  return (
    <div className="space-y-8">
      <HivePageHeader
        title="Agents"
        subtitle="Unified control plane for supervisor sessions, active bees, and hierarchy topology."
        info={{
          title: "Agents + Supervisor",
          description: "Riadenie Supervisor sessions, aktívnych agentov a rozhodovacích krokov.",
          options: ["Approve/Reject flows", "Spawn agent", "Hierarchy kontrola"],
        }}
        actions={
          <div className="flex items-center gap-3">
            <span className="font-(family-name:--font-poppins) text-xs tabular-nums text-zinc-500">
              {rows.length} bees
            </span>
            <Link
              href="/agents/new"
              className="qs-btn qs-btn--ghost qs-btn--sm whitespace-nowrap"
              prefetch={false}
            >
              + Spawn agent
            </Link>
          </div>
        }
      />
      <section id="sessions" className="space-y-4 rounded-3xl border border-cyan/20 bg-[#080d16]/70 p-4 md:p-6">
        <header className="space-y-1">
          <h2 className="text-base font-semibold text-zinc-100 md:text-lg">Supervisor sessions</h2>
          <p className="text-xs text-zinc-400 md:text-sm">
            Light control-plane first: approve/reject loops, needs_input handling, and routine orchestration.
          </p>
        </header>
        <AgentsSessionsPanel />
      </section>

      <section id="active-agents" className="space-y-4 rounded-3xl border border-zinc-800/80 bg-[#070b13]/70 p-4 md:p-6">
        <header className="space-y-1">
          <h2 className="text-base font-semibold text-zinc-100 md:text-lg">Active agents</h2>
          <p className="text-xs text-zinc-400 md:text-sm">
            Live roster, health/status, and direct actions for each bee in one scanable board.
          </p>
        </header>
        <AgentsPageRoster initialAgents={rows} />
      </section>

      <section id="hierarchy" className="space-y-4 rounded-3xl border border-zinc-800/80 bg-[#070b13]/70 p-4 md:p-6">
        <header className="space-y-1">
          <h2 className="text-base font-semibold text-zinc-100 md:text-lg">Hierarchy graph</h2>
          <p className="text-xs text-zinc-400 md:text-sm">
            Queen → managers → workers topology with grouped swarm lanes and unassigned workers.
          </p>
        </header>
        <HierarchyPageConsole showHeader={false} />
      </section>

      {rows.length === 0 ? (
        <p className="text-sm font-(family-name:--font-poppins) text-muted-foreground">
          No bees yet — bootstrap through backend/scripts/hive_seed.py.
        </p>
      ) : null}
    </div>
  );
}
