import { HivePageHeader } from "@/components/hive/hive-page-header";
import { WorkflowDagHero } from "@/components/hive/workflow-dag-hero";
import { NeonButton } from "@/components/ui/neon-button";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { WorkflowRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

export const dynamic = "force-dynamic";

function pct(wf: WorkflowRow): number {
  if (!wf.total_steps) return 0;
  return Math.round((wf.completed_steps / wf.total_steps) * 100);
}

function wfStripe(wf: WorkflowRow): string {
  const status = wf.status.toUpperCase();
  if (status.includes("COMPLETE")) return "bg-data";
  if (status.includes("PENDING")) return "bg-pollen";
  if (status.includes("RUN")) return "bg-success";
  return "bg-alert";
}

export default async function WorkflowsPage() {
  const workflows = await hiveServerRawJson<WorkflowRow[]>("/workflows?limit=50");

  if (!workflows) {
    return <p className="font-[family-name:var(--font-jetbrains-mono)] text-sm text-danger">Workflow shards unavailable.</p>;
  }

  const [hero, ...rest] = workflows;

  return (
    <div className="space-y-10">
      <HivePageHeader title="Workflows" subtitle="DAG executions · Auto Workflow Breaker decomposes hostile tasks · guardrails per step." />
      {hero ? <WorkflowDagHero workflow={hero} /> : null}

      <section className="space-y-3">
        {(hero ? rest : workflows).map((wf) => {
          const p = pct(wf);
          return (
            <article
              key={wf.id}
              className="relative flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-cyan/[0.1] bg-hive-card/90 p-4 md:p-5"
            >
              <span aria-hidden className={cn("absolute inset-y-0 left-0 w-1 rounded-l-2xl", wfStripe(wf))} />
              <div className="min-w-0 pt-1 pl-3 font-[family-name:var(--font-inter)]">
                <p className="font-semibold text-[#fafafa]">{wf.original_task_text}</p>
                <div className="mt-2 flex flex-wrap gap-2 font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.12em] text-zinc-500">
                  <span>{wf.status.replaceAll("_", " ")}</span>
                  <span>{wf.completed_steps}/{wf.total_steps}</span>
                </div>
              </div>
              <div className="flex items-center gap-4 pl-3">
                <div className="w-36">
                  <p className="text-right font-[family-name:var(--font-space-grotesk)] text-xl text-pollen tabular-nums">{p}%</p>
                  <div className="mt-2 h-1.5 rounded-full bg-black/50">
                    <div className={cn("h-full rounded-full", wfStripe(wf))} style={{ width: `${p}%`, opacity: 0.92 }} />
                  </div>
                </div>
                <NeonButton type="button" variant="ghost" className="text-xs uppercase">
                  Open
                </NeonButton>
              </div>
            </article>
          );
        })}
      </section>

      {workflows.length === 0 ? (
        <p className="font-[family-name:var(--font-inter)] text-sm text-muted-foreground">
          No workflows yet — submit a backlog task plus POST `/workflows/decompose`.
        </p>
      ) : null}
    </div>
  );
}
