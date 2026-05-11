import { hiveServerRawJson } from "@/lib/hive-server";
import type { WorkflowRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

export default async function WorkflowsPage() {
  const workflows = await hiveServerRawJson<WorkflowRow[]>("/workflows?limit=50");

  if (!workflows) {
    return (
      <p className="text-danger font-[family-name:var(--font-jetbrains-mono)] text-sm">Workflow shards unavailable.</p>
    );
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-[family-name:var(--font-space-grotesk)] text-3xl font-semibold text-pollen">
          Auto Workflow Breaker plans
        </h1>
        <p className="font-[family-name:var(--font-jetbrains-mono)] text-sm text-cyan">
          Each row is guardrailed graph materialized from LiteLLM decomposition + LangGraph supervisors.
        </p>
      </header>
      <div className="space-y-3">
        {workflows.map((wf) => (
          <article key={wf.id} className="rounded-3xl border border-pollen/30 bg-black/35 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs uppercase tracking-[0.25em] text-data">
                {wf.status.replaceAll("_", " ")}
              </p>
              <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-muted-foreground">
                steps {wf.completed_steps}/{wf.total_steps}
              </p>
            </div>
            <p className="mt-4 font-[family-name:var(--font-space-grotesk)] text-lg text-[#FFB800]">{wf.original_task_text}</p>
            {wf.matching_recipe_id ? (
              <p className="mt-3 font-[family-name:var(--font-jetbrains-mono)] text-xs text-[#00FF88]">
                recipe anchor {wf.matching_recipe_id}
              </p>
            ) : (
              <p className="mt-3 font-[family-name:var(--font-jetbrains-mono)] text-xs text-cyan">
                Chrom hints cold · hive still searching imitation templates.
              </p>
            )}
          </article>
        ))}
      </div>
      {workflows.length === 0 ? (
        <p className="font-[family-name:var(--font-jetbrains-mono)] text-sm text-muted-foreground">
          No workflows persisted yet · submit a backlog task plus POST `/workflows/decompose`.
        </p>
      ) : null}
    </div>
  );
}
