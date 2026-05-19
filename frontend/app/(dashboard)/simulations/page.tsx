import { ConfettiTrigger } from "@/components/hive/confetti-trigger";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import { PendingReviewPanel } from "@/components/hive/pending-review-panel";
import { V4PageCanvas } from "@/components/ui/v4";
import { SIMULATIONS_ENABLED } from "@/lib/feature-flags";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { SimulationRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

const HEADER_SUBTITLE =
  "Only payloads that survived dockerized guardrails bubble up to ballroom operators — ignite confetti whenever a new sandbox goes green.";

export default async function SimulationsPage() {
  if (!SIMULATIONS_ENABLED) {
    return (
      <V4PageCanvas className="gap-6">
        <HivePageHeader title="Verified simulation vault" subtitle={HEADER_SUBTITLE} />
        <div className="rounded-2xl border border-cyan/20 bg-black/30 p-5">
          <p className="font-[family-name:var(--font-poppins)] text-sm text-zinc-300">
            Simulations module is disabled. Enable <code>NEXT_PUBLIC_SIMULATIONS_ENABLED=true</code> for this section.
          </p>
        </div>
      </V4PageCanvas>
    );
  }

  const audits = await hiveServerRawJson<SimulationRow[]>("/simulations?limit=50");

  return (
    <V4PageCanvas className="gap-8">
      <HivePageHeader
        title="Verified simulation vault"
        subtitle={HEADER_SUBTITLE}
        actions={<ConfettiTrigger />}
      />

      {!audits ? (
        <p className="text-danger font-[family-name:var(--font-poppins)] text-sm">
          Simulation ledger unavailable · docker probes remain opt-in (`SIMULATION_DOCKER_EXECUTION_ENABLED`).
        </p>
      ) : (
        <>
          <PendingReviewPanel />

          <div className="v4-simulation-grid">
            {audits.map((audit) => (
              <article
                key={audit.id}
                className="rounded-3xl border border-success/35 bg-black/35 p-4 shadow-[0_0_42px_rgba(0,255,136,0.18)] md:p-5"
              >
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
        </>
      )}
    </V4PageCanvas>
  );
}
