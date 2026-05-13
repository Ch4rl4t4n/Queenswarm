import { ConfettiTrigger } from "@/components/hive/confetti-trigger";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { SimulationRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

export default async function SimulationsPage() {
  const audits = await hiveServerRawJson<SimulationRow[]>("/simulations?limit=50");

  if (!audits) {
    return (
      <p className="text-danger font-[family-name:var(--font-poppins)] text-sm">
        Simulation ledger unavailable · docker probes remain opt-in (`SIMULATION_DOCKER_EXECUTION_ENABLED`).
      </p>
    );
  }

  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <h1 className="font-[family-name:var(--font-poppins)] text-3xl font-semibold text-pollen">
            verified simulation vault
          </h1>
          <p className="mt-2 max-w-2xl font-[family-name:var(--font-poppins)] text-sm text-cyan">
            Only payloads that survived dockerized guardrails bubble up to ballroom operators — ignite confetti whenever a
            new sandbox goes green.
          </p>
        </div>
        <ConfettiTrigger />
      </header>
      <div className="grid gap-4 md:grid-cols-2">
        {audits.map((audit) => (
          <article key={audit.id} className="rounded-3xl border border-success/35 bg-black/35 p-5 shadow-[0_0_42px_rgba(0,255,136,0.18)]">
            <p className="font-[family-name:var(--font-poppins)] text-xs uppercase tracking-[0.25em] text-data">
              {audit.result_type}
            </p>
            <p className="mt-4 font-[family-name:var(--font-poppins)] text-sm text-muted-foreground">
              confidence {audit.confidence_pct ?? 0}%
            </p>
            <p className="mt-4 font-[family-name:var(--font-poppins)] text-xs text-muted-foreground">
              task {audit.task_id ?? "n/a"}
            </p>
            <p className="font-[family-name:var(--font-poppins)] text-[11px] text-muted-foreground">
              {audit.created_at ? new Date(audit.created_at).toISOString() : "timestamp pending"}
            </p>
          </article>
        ))}
      </div>
      {audits.length === 0 ? (
        <p className="font-[family-name:var(--font-poppins)] text-sm text-muted-foreground">
          No audited simulations yet · route a swarm cycle with evaluation + simulator agents to populate Postgres rows.
        </p>
      ) : null}
    </div>
  );
}
