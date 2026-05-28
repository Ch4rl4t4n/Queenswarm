"use client";

import Link from "next/link";

import { HivePageShell } from "@/components/hive/hive-page-shell";
import { PendingReviewPanel } from "@/components/hive/pending-review-panel";
import { TASKS_HUB_PATH, WORKFLOWS_PATH } from "@/lib/execution-lane-routes";
import type { SimulationRow } from "@/lib/hive-types";

const SIMULATIONS_SUBTITLE =
  "Only payloads that survived dockerized guardrails bubble up to ballroom operators.";

interface SimulationsPageClientProps {
  audits: SimulationRow[] | null;
  /** Module disabled via feature flag — render shell with operator hint. */
  disabled?: boolean;
}

export function SimulationsPageClient({ audits, disabled = false }: SimulationsPageClientProps): JSX.Element {
  if (disabled) {
    return (
      <HivePageShell title="Simulations" subtitle={SIMULATIONS_SUBTITLE}>
        <div className="rounded-2xl border border-cyan/20 bg-black/30 p-5">
          <p className="font-[family-name:var(--font-poppins)] text-sm text-zinc-300">
            Simulations module is disabled. Enable{" "}
            <code className="text-(--qs-cyan)">NEXT_PUBLIC_SIMULATIONS_ENABLED=true</code> for this section.
          </p>
        </div>
      </HivePageShell>
    );
  }

  return (
    <HivePageShell
      title="Simulations"
      subtitle={SIMULATIONS_SUBTITLE}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link href={TASKS_HUB_PATH} className="qs-btn qs-btn--ghost qs-btn--sm">
            Tasks hub
          </Link>
          <Link href={WORKFLOWS_PATH} className="qs-btn qs-btn--ghost qs-btn--sm">
            Workflows
          </Link>
        </div>
      }
    >
      {!audits ? (
        <p className="text-danger font-[family-name:var(--font-poppins)] text-sm" role="alert">
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
              No audited simulations yet · route a swarm cycle with evaluation + simulator agents to populate Postgres
              rows.
            </p>
          ) : null}
        </>
      )}
    </HivePageShell>
  );
}
