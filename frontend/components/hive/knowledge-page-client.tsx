"use client";

import Link from "next/link";
import {
  BookOpen,
  Flag,
  GitBranch,
  Layers,
  Mic,
  Moon,
  Plus,
  Save,
  Sparkles,
} from "lucide-react";
import { useState } from "react";

import { CuratedMemoryPanel } from "@/components/hive/curated-memory-panel";
import { DreamingConsole } from "@/components/hive/dreaming-console";
import { GoalsPanel } from "@/components/hive/goals-panel";
import { HiveMindExplorer } from "@/components/hive/hive-mind-explorer";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import { LearningConsole } from "@/components/hive/learning-console";
import { MemoryEvolutionPanel } from "@/components/hive/memory-evolution-panel";
import { OutputsInteractivePanel } from "@/components/hive/outputs-interactive-panel";
import { RecipesPageClient } from "@/components/hive/recipes-page-client";
import {
  V4Card,
  V4CardHeader,
  V4SearchInput,
  V4PageCanvas,
} from "@/components/ui/v4";
import { RECIPES_ENABLED } from "@/lib/feature-flags";
import type { FinalDeliverableSummaryRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

type KnowledgeTab = "hivemind" | "outputs" | "recipes" | "dreaming" | "memory" | "goals";

interface KnowledgePageClientProps {
  initialOutputs: FinalDeliverableSummaryRow[];
  /** SSR archive fetch failed — tab panels still render; outputs tab may be empty until poll. */
  archiveSyncPending?: boolean;
}

const TABS: { id: KnowledgeTab; label: string; icon: typeof GitBranch }[] = [
  { id: "hivemind", label: "HiveMind", icon: GitBranch },
  { id: "outputs", label: "Outputs · Archive", icon: Save },
  { id: "recipes", label: "Recipes · Learning", icon: BookOpen },
  { id: "dreaming", label: "Dreaming", icon: Moon },
  { id: "memory", label: "Curated memory", icon: Layers },
  { id: "goals", label: "Goals", icon: Flag },
];

export function KnowledgePageClient({ initialOutputs, archiveSyncPending = false }: KnowledgePageClientProps) {
  const [tab, setTab] = useState<KnowledgeTab>("hivemind");
  const [filter, setFilter] = useState("");

  return (
    <V4PageCanvas>
      {archiveSyncPending ? (
        <p className="rounded-xl border border-alert/30 bg-alert/10 px-4 py-3 text-sm text-(--qs-text-2) lg:hidden">
          Knowledge archive syncing — retrieval panels remain available.
        </p>
      ) : null}
      <HivePageHeader
        title="Knowledge"
        subtitle="One plane — HiveMind retrieval, outputs archive, recipes/learning, dreaming cycles, curated memory, goals."
        actions={
          <div className="v4-page-header-actions-group flex flex-wrap items-center gap-2">
            <Link href="/agents#sessions" className="qs-btn qs-btn--ghost qs-btn--sm gap-2">
              <Sparkles className="h-4 w-4" aria-hidden />
              Retrieval session
            </Link>
            <Link href="/tasks/new" className="qs-btn qs-btn--ghost qs-btn--sm gap-2">
              <Plus className="h-4 w-4" aria-hidden />
              New task
            </Link>
            <Link href="/ballroom" className="qs-btn qs-btn--primary qs-btn--sm gap-2">
              <Mic className="h-4 w-4" aria-hidden />
              Ballroom
            </Link>
          </div>
        }
      />

      <div className="v4-subtab-row w-full max-w-full">
        {TABS.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              type="button"
              className={cn("v4-subtab", tab === item.id && "v4-subtab--active")}
              onClick={() => setTab(item.id)}
            >
              <Icon className="h-3.5 w-3.5" aria-hidden />
              {item.label}
            </button>
          );
        })}
      </div>

      <V4Card>
        <V4CardHeader
          kicker="Knowledge command center"
          title="Retrieval contract"
          description="Unified lens for retrieval: contract context, output archive, recipe / dreaming loops."
        />
        <V4SearchInput
          value={filter}
          onChange={setFilter}
          placeholder="Filter blocks · graph, archive, pollen, recipes…"
          className="mb-4"
        />
        <div className="v4-cols-2">
          <div className="v4-knowledge-contract v4-knowledge-contract--purple">
            <span className="v4-label-kicker">Retrieval contract</span>
            <p className="v4-knowledge-mono">customer_history + policy + last_3_tasks</p>
            <p className="v4-knowledge-foot">Used by Queen for every new mission brief.</p>
          </div>
          <div className="v4-knowledge-contract v4-knowledge-contract--gold">
            <span className="v4-label-kicker">Skill pack preset</span>
            <p className="v4-knowledge-mono v4-knowledge-mono--purple">context + decide + tdd + diagnose</p>
            <p className="v4-knowledge-foot">Active across Eval &amp; Action swarms.</p>
          </div>
        </div>
      </V4Card>

      {tab === "hivemind" ? (
        <>
          <V4Card>
            <V4CardHeader
              title="HiveMind · graph + vault + search"
              description="Neo4j semantic graph · ChromaDB vector fallback · retrieval-aware prompting."
              actions={
                <div className="flex flex-wrap gap-2">
                  <Link href="/tasks/new" className="qs-btn qs-btn--ghost qs-btn--sm">
                    Quick ingest · task
                  </Link>
                  <Link href="/agents#sessions" className="qs-btn qs-btn--ghost qs-btn--sm">
                    Quick ingest · supervisor
                  </Link>
                </div>
              }
            />
            <HiveMindExplorer showHeader={false} variant="v4" filterHint={filter} />
          </V4Card>
          <MemoryEvolutionPanel />
        </>
      ) : null}

      {tab === "outputs" ? (
        <V4Card>
          <V4CardHeader
            title="Outputs &amp; archive"
            description="Semantic archive search · regenerate · PDF / markdown export in one operator loop."
          />
          <OutputsInteractivePanel initialItems={initialOutputs} />
        </V4Card>
      ) : null}

      {tab === "recipes" ? (
        <div className="space-y-6">
          <LearningConsole showHeader={false} variant="v4" />
          {RECIPES_ENABLED ? (
            <RecipesPageClient showHeader={false} />
          ) : (
            <V4Card>
              <p className="text-sm text-(--qs-text-3)">
                Recipes module is disabled. Enable <code>NEXT_PUBLIC_RECIPES_ENABLED=true</code> for saved workflow catalog.
              </p>
            </V4Card>
          )}
        </div>
      ) : null}

      {tab === "dreaming" ? <DreamingConsole /> : null}

      {tab === "memory" ? <CuratedMemoryPanel /> : null}

      {tab === "goals" ? <GoalsPanel /> : null}
    </V4PageCanvas>
  );
}
