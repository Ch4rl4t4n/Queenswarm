import { ColonyConsole } from "@/components/hive/colony-console";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { AgentRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

export default async function HiveHomeDashboard() {
  const agents = await hiveServerRawJson<AgentRow[]>("/agents?limit=200");

  if (!agents) {
    return (
      <div className="rounded-3xl border border-alert/35 bg-black/60 p-8 text-alert">
        <p className="font-[family-name:var(--font-poppins)] text-xl font-semibold text-pollen">
          Agent list unavailable
        </p>
        <p className="mt-4 max-w-xl font-[family-name:var(--font-poppins)] text-sm leading-relaxed text-zinc-400">
          Check that you&apos;re signed in. For local dev the API must be running on port 8000 or set
          INTERNAL_BACKEND_ORIGIN.
        </p>
      </div>
    );
  }

  return (
    <div className="pb-8">
      <ColonyConsole initialAgents={agents} />
    </div>
  );
}
