import { hiveServerRawJson } from "@/lib/hive-server";
import type { SubSwarmRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

export default async function SwarmsPage() {
  const colonies = await hiveServerRawJson<SubSwarmRow[]>("/swarms?limit=50");

  if (!colonies) {
    return (
      <p className="text-danger font-[family-name:var(--font-jetbrains-mono)] text-sm">
        Colony catalog unreachable — inspect backend bearer token routing.
      </p>
    );
  }

  return (
    <div className="space-y-8">
      <header>
        <h1 className="font-[family-name:var(--font-space-grotesk)] text-3xl font-semibold text-pollen">
          sub-swarm colonies
        </h1>
        <p className="mt-3 max-w-3xl font-[family-name:var(--font-jetbrains-mono)] text-sm text-cyan">
          Scout · Evaluator · Simulator · Reporter partitions carry local hive memory and sync deltas into the planetary
          graph on the five-minute beacon.
        </p>
      </header>
      <div className="grid gap-5 md:grid-cols-2">
        {colonies.map((swarm) => (
          <article
            key={swarm.id}
            className="rounded-[28px] border border-[#00FFFF]/30 bg-black/35 p-6 shadow-[0_26px_64px_rgba(0,0,0,0.55)]"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs uppercase tracking-[0.24em] text-data">
                  {swarm.purpose.toLowerCase().replace("_", " ")}
                </p>
                <h2 className="font-[family-name:var(--font-space-grotesk)] text-2xl font-semibold text-pollen">{swarm.name}</h2>
              </div>
              <span
                className={
                  swarm.is_active
                    ? "font-[family-name:var(--font-jetbrains-mono)] text-xs text-success"
                    : "font-[family-name:var(--font-jetbrains-mono)] text-xs text-danger"
                }
              >
                {swarm.is_active ? "active" : "dormant"}
              </span>
            </div>
            <dl className="mt-6 grid gap-4 font-[family-name:var(--font-jetbrains-mono)] text-sm text-[#CCFFFF]/90 sm:grid-cols-3">
              <div>
                <dt className="text-xs uppercase text-muted-foreground">bees tracked</dt>
                <dd>{swarm.member_count}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase text-muted-foreground">pollen held</dt>
                <dd>{Number(swarm.total_pollen).toFixed(2)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase text-muted-foreground">last global sync</dt>
                <dd>{swarm.last_global_sync_at ? new Date(swarm.last_global_sync_at).toUTCString() : "awaiting beacon"}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </div>
  );
}
