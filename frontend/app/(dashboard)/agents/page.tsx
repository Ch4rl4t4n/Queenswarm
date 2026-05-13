import Link from "next/link";

import { AgentsPageRoster } from "@/components/hive/agents-page-roster";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { AgentRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

export default async function AgentsPage() {
  const rows = await hiveServerRawJson<AgentRow[]>("/agents?limit=120");

  if (!rows) {
    return <p className="font-[family-name:var(--font-poppins)] text-sm text-danger">Could not sync agents ledger.</p>;
  }

  return (
    <div className="space-y-8">
      <HivePageHeader
        title="Agents"
        subtitle="Live roster · imitate top pollinators · every bee runs one disciplined job."
        actions={
          <div className="flex items-center gap-3">
            <span className="font-[family-name:var(--font-poppins)] text-xs tabular-nums text-zinc-500">
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
      <AgentsPageRoster initialAgents={rows} />
      {rows.length === 0 ? (
        <p className="text-sm font-[family-name:var(--font-poppins)] text-muted-foreground">
          No bees yet — bootstrap through backend/scripts/hive_seed.py.
        </p>
      ) : null}
    </div>
  );
}
