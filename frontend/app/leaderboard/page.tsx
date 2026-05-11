import { hiveServerRawJson } from "@/lib/hive-server";
import type { AgentRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

export default async function LeaderboardPage() {
  const agents = await hiveServerRawJson<AgentRow[]>("/agents?limit=200");

  if (!agents) {
    return <p className="text-danger text-sm font-[family-name:var(--font-jetbrains-mono)]">Agent telemetry unavailable.</p>;
  }

  const ranked = [...agents].sort((a, b) => b.pollen_points - a.pollen_points).slice(0, 120);

  return (
    <div className="space-y-8">
      <header>
        <h1 className="font-[family-name:var(--font-space-grotesk)] text-4xl font-semibold text-pollen">
          imitation leaderboard
        </h1>
        <p className="mt-3 max-w-3xl font-[family-name:var(--font-jetbrains-mono)] text-sm text-cyan">
          Pollen-ranked bees become exemplars · neighbor bees copy choreography when similarity beats trust thresholds.
        </p>
      </header>
      <div className="overflow-hidden rounded-3xl border border-pollen/30">
        <table className="w-full border-collapse text-left font-[family-name:var(--font-jetbrains-mono)] text-sm text-[#D8FFFF]/90">
          <thead className="bg-black/65 text-[11px] uppercase tracking-[0.25em] text-data">
            <tr>
              <th className="px-6 py-3">rank</th>
              <th className="px-6 py-3">bee</th>
              <th className="px-6 py-3">role</th>
              <th className="px-6 py-3">status</th>
              <th className="px-6 py-3 text-right">pollen</th>
              <th className="px-6 py-3 text-right">τ perf</th>
            </tr>
          </thead>
          <tbody>
            {ranked.map((agent, idx) => (
              <tr key={agent.id} className="border-t border-cyan/10 odd:bg-black/35 even:bg-transparent">
                <td className="px-6 py-4 text-muted-foreground">#{idx + 1}</td>
                <td className="px-6 py-4 text-[#FFB800]">{agent.name}</td>
                <td className="px-6 py-4">{agent.role}</td>
                <td className="px-6 py-4 text-alert">{agent.status}</td>
                <td className="px-6 py-4 text-right text-success">{Number(agent.pollen_points).toFixed(3)}</td>
                <td className="px-6 py-4 text-right text-cyan">{Number(agent.performance_score ?? 0).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
