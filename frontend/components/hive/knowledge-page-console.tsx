"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { DreamingConsole } from "@/components/hive/dreaming-console";
import { HiveMindExplorer } from "@/components/hive/hive-mind-explorer";
import { InfoHint } from "@/components/hive/info-hint";
import { LearningConsole } from "@/components/hive/learning-console";
import { OutputsInteractivePanel } from "@/components/hive/outputs-interactive-panel";
import { RecipesPageClient } from "@/components/hive/recipes-page-client";
import { ResearchBeePanel } from "@/components/hive/research-bee-panel";
import type { FinalDeliverableSummaryRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

type KnowledgeSection = "all" | "hivemind" | "outputs" | "recipes" | "dreaming";

interface KnowledgePageConsoleProps {
  readonly initialOutputs: FinalDeliverableSummaryRow[];
  readonly recipesEnabled: boolean;
}

const SECTION_COPY: Record<Exclude<KnowledgeSection, "all">, string> = {
  hivemind: "graph vault semantic search retrieval contract skills memory",
  outputs: "archive outputs regenerate semantic markdown lineage",
  recipes: "learning pollen rewards recipes imitation reflection skills",
  dreaming: "memory dreaming consolidation lessons learned supervisor reports",
};

export function KnowledgePageConsole({ initialOutputs, recipesEnabled }: KnowledgePageConsoleProps): JSX.Element {
  const [focus, setFocus] = useState<KnowledgeSection>("all");
  const [filterText, setFilterText] = useState("");
  const [researchError, setResearchError] = useState<string | null>(null);

  const q = filterText.trim().toLowerCase();
  const visible = useMemo(
    () => ({
      hivemind:
        (focus === "all" || focus === "hivemind") &&
        (q.length === 0 || SECTION_COPY.hivemind.includes(q)),
      outputs:
        (focus === "all" || focus === "outputs") &&
        (q.length === 0 || SECTION_COPY.outputs.includes(q)),
      recipes:
        (focus === "all" || focus === "recipes") &&
        (q.length === 0 || SECTION_COPY.recipes.includes(q)),
      dreaming:
        (focus === "all" || focus === "dreaming") &&
        (q.length === 0 || SECTION_COPY.dreaming.includes(q)),
    }),
    [focus, q],
  );

  return (
    <div className="scroll-smooth space-y-8">
      <section className="sticky top-2 z-10 space-y-4 rounded-2xl border border-[color:var(--qs-border)] bg-[#060b12]/90 p-4 backdrop-blur">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <p className="text-xs uppercase tracking-[0.14em] text-cyan">Knowledge command center</p>
              <InfoHint
                title="Knowledge command center"
                description="Controls retrieval context, output archive, and recipe learning loops."
                options={["Filter focus", "Quick links", "Retrieval contract context"]}
              />
            </div>
            <p className="text-xs text-zinc-400">
              Unified lane for retrieval contract context, output archive actions, and learning/recipe loops.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/agents#sessions" className="qs-btn qs-btn--ghost qs-btn--sm">
              Start retrieval session
            </Link>
            <Link href="/tasks/new" className="qs-btn qs-btn--ghost qs-btn--sm">
              New task
            </Link>
            <Link href="/ballroom" className="qs-btn qs-btn--ghost qs-btn--sm">
              Open Ballroom
            </Link>
          </div>
        </div>

        <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
          <div className="flex items-center gap-2">
            <input
              value={filterText}
              onChange={(event) => setFilterText(event.target.value)}
              placeholder="Filter blocks: graph, archive, pollen, recipes..."
              className="qs-input"
            />
            <InfoHint
              title="Knowledge filter"
              description="Filters visible knowledge blocks by keywords."
              options={["Graph/HiveMind", "Outputs archive", "Recipes/Learning"]}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {(["all", "hivemind", "outputs", "recipes", "dreaming"] as const).map((option) => (
              <button
                key={option}
                type="button"
                className={cn("qs-btn qs-btn--sm", focus === option ? "qs-btn--primary" : "qs-btn--ghost")}
                onClick={() => setFocus(option)}
              >
                {option}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap gap-2 text-xs">
          <a href="#hivemind" className="rounded-full border border-[color:var(--qs-border-2)] px-2 py-1 text-cyan">
            #hivemind
          </a>
          <a href="#outputs" className="rounded-full border border-[color:var(--qs-border-2)] px-2 py-1 text-cyan">
            #outputs
          </a>
          <a href="#recipes" className="rounded-full border border-[color:var(--qs-border-2)] px-2 py-1 text-cyan">
            #recipes
          </a>
          <a href="#dreaming" className="rounded-full border border-[color:var(--qs-border-2)] px-2 py-1 text-cyan">
            #dreaming
          </a>
        </div>

        <div className="grid gap-2 text-xs text-zinc-300 sm:grid-cols-2">
          <div className="rounded-xl border border-zinc-800 bg-black/25 px-3 py-2">
            <p className="uppercase tracking-widest text-zinc-500">Retrieval contract</p>
            <p className="mt-1 font-mono text-[11px] text-cyan">customer_history + policy + last_3_tasks</p>
          </div>
          <div className="rounded-xl border border-zinc-800 bg-black/25 px-3 py-2">
            <p className="uppercase tracking-widest text-zinc-500">Skill pack preset</p>
            <p className="mt-1 font-mono text-[11px] text-pollen">context + decide + tdd + diagnose</p>
          </div>
        </div>
      </section>

      {visible.hivemind ? (
        <section id="hivemind" className="space-y-4 rounded-3xl border border-[color:var(--qs-border)] bg-[#070d17]/70 p-4 md:p-6">
          <header className="space-y-1">
            <h2 className="text-base font-semibold text-zinc-100 md:text-lg">HiveMind (graph + vault + search)</h2>
            <p className="text-xs text-zinc-400 md:text-sm">
              Semantic graph exploration, vault export, and recall preview for retrieval-contract aware prompting.
            </p>
          </header>
          <div className="flex flex-wrap gap-2">
            <Link href="/tasks/new" className="qs-btn qs-btn--ghost qs-btn--sm">
              Quick ingest via task
            </Link>
            <Link href="/agents#sessions" className="qs-btn qs-btn--ghost qs-btn--sm">
              Quick ingest via supervisor
            </Link>
          </div>
          <HiveMindExplorer showHeader={false} />
          <ResearchBeePanel onError={setResearchError} />
          {researchError ? <p className="text-xs text-[#FF3366]">{researchError}</p> : null}
        </section>
      ) : null}

      {visible.outputs ? (
        <section id="outputs" className="space-y-4 rounded-3xl border border-zinc-800/80 bg-[#070b13]/70 p-4 md:p-6">
          <header className="space-y-1">
            <h2 className="text-base font-semibold text-zinc-100 md:text-lg">Outputs / Archive</h2>
            <p className="text-xs text-zinc-400 md:text-sm">
              Semantic archive search with regenerate + markdown export actions in one operator loop.
            </p>
          </header>
          <OutputsInteractivePanel initialItems={initialOutputs} />
        </section>
      ) : null}

      {visible.recipes ? (
        <section id="recipes" className="space-y-6 rounded-3xl border border-zinc-800/80 bg-[#070b13]/70 p-4 md:p-6">
          <header className="space-y-1">
            <h2 className="text-base font-semibold text-zinc-100 md:text-lg">Knowledge / Recipes / Learning</h2>
            <p className="text-xs text-zinc-400 md:text-sm">
              Pollen rewards, imitation, reflections, and recipe recall for reusable verified workflows.
            </p>
          </header>
          <LearningConsole showHeader={false} />
          {recipesEnabled ? (
            <RecipesPageClient showHeader={false} />
          ) : (
            <p className="rounded-2xl border border-[color:var(--qs-border)] bg-black/30 p-4 text-sm text-zinc-300">
              Recipes module is disabled. Enable <code>NEXT_PUBLIC_RECIPES_ENABLED=true</code> for saved workflow catalog.
            </p>
          )}
        </section>
      ) : null}

      {visible.dreaming ? (
        <section id="dreaming">
          <DreamingConsole />
        </section>
      ) : null}

      {!visible.hivemind && !visible.outputs && !visible.recipes && !visible.dreaming ? (
        <p className="rounded-2xl border border-zinc-800 bg-black/25 p-4 text-sm text-zinc-400">
          No blocks match this filter. Clear search or switch focus to <code>all</code>.
        </p>
      ) : null}
    </div>
  );
}
