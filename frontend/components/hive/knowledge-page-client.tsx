"use client";

import Link from "next/link";
import {
  BookOpen,
  BookMarked,
  Flag,
  GitBranch,
  Layers,
  Moon,
  Network,
  Save,
  Search,
  Sparkles,
  Waypoints,
} from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useState, useEffect, useCallback, useMemo } from "react";

import { AutoGraphifyPanel } from "@/components/hive/auto-graphify-panel";
import { SelectiveRecallPanel } from "@/components/hive/selective-recall-panel";
import { ProjectShapeGraphPanel } from "@/components/hive/project-shape-graph-panel";
import { OperatorBrainPackPanel } from "@/components/hive/operator-brain-pack-panel";
import { HiveSessionSearchPanel } from "@/components/hive/hive-session-search-panel";
import { EpisodicMemoryPanel } from "@/components/hive/episodic-memory-panel";
import { DreamingConsole } from "@/components/hive/dreaming-console";
import { GoalsPanel } from "@/components/hive/goals-panel";
import { HiveMindExplorer } from "@/components/hive/hive-mind-explorer";
import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HiveSectionSubnav } from "@/components/hive/hive-section-subnav";
import { HiveSubnavContent } from "@/components/hive/hive-subnav-stack";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { LearningConsole } from "@/components/hive/learning-console";
import { MemoryEvolutionPanel } from "@/components/hive/memory-evolution-panel";
import { OutputsInteractivePanel } from "@/components/hive/outputs-interactive-panel";
import { RecipesPageClient } from "@/components/hive/recipes-page-client";
import { ResearchBeePanel } from "@/components/hive/research-bee-panel";
import { WikiLayerPanel } from "@/components/hive/wiki-layer-panel";
import {
  V4Card,
  V4CardHeader,
  V4SearchInput,
} from "@/components/ui/v4";
import { RECIPES_ENABLED } from "@/lib/feature-flags";
import type { FinalDeliverableSummaryRow } from "@/lib/hive-types";
import {
  knowledgeHivemindSectionFromHash,
  knowledgeHivemindSectionHref,
  resolveKnowledgeHivemindSection,
  type KnowledgeHivemindSection,
} from "@/lib/knowledge-hivemind-routes";
import {
  knowledgeTabFromHash,
  knowledgeTabHref,
  resolveKnowledgeTab,
  type KnowledgeTab,
} from "@/lib/knowledge-routes";

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
  { id: "wiki", label: "Wiki Layer", icon: BookMarked },
  { id: "goals", label: "Goals", icon: Flag },
];

const HIVEMIND_SECTIONS: {
  id: KnowledgeHivemindSection;
  label: string;
  icon: typeof Network;
}[] = [
  { id: "graphify", label: "Auto graphify", icon: Network },
  { id: "shape", label: "Project shape", icon: Waypoints },
  { id: "recall", label: "Selective recall", icon: Sparkles },
  { id: "ingest", label: "Ingest URL", icon: BookOpen },
  { id: "explorer", label: "Graph + search", icon: Search },
  { id: "evolution", label: "Memory evolution", icon: GitBranch },
];

export function KnowledgePageClient({ initialOutputs, archiveSyncPending = false }: KnowledgePageClientProps) {
  const searchParams = useSearchParams();
  const foragerId = searchParams.get("forager")?.trim() ?? "";
  const foragerSearchQ = searchParams.get("q")?.trim() ?? "";

  const tabIds = useMemo(() => TABS.map((item) => item.id), []);

  const [tab, setTab] = useState<KnowledgeTab>(() => resolveKnowledgeTab({ visibleTabIds: tabIds }));
  const [hivemindSection, setHivemindSection] = useState<KnowledgeHivemindSection>(() =>
    resolveKnowledgeHivemindSection({ hash: typeof window !== "undefined" ? window.location.hash : "" }),
  );
  const [filter, setFilter] = useState("");
  const [ingestError, setIngestError] = useState<string | null>(null);

  const selectTab = useCallback((next: KnowledgeTab) => {
    setTab(next);
    const href = knowledgeTabHref(next);
    window.history.replaceState(null, "", href);
  }, []);

  const selectHivemindSection = useCallback((next: KnowledgeHivemindSection) => {
    setTab("hivemind");
    setHivemindSection(next);
    window.history.replaceState(null, "", knowledgeHivemindSectionHref(next));
  }, []);

  useEffect(() => {
    if (!foragerId) {
      return;
    }
    setTab("hivemind");
    setHivemindSection("explorer");
    if (foragerSearchQ) {
      setFilter(foragerSearchQ);
    }
  }, [foragerId, foragerSearchQ]);

  useEffect(() => {
    const syncFromHash = (): void => {
      const hash = window.location.hash;
      const hivemindFromHash = knowledgeHivemindSectionFromHash(hash);
      if (hivemindFromHash) {
        setTab("hivemind");
        setHivemindSection(hivemindFromHash);
        return;
      }
      const fromHash = knowledgeTabFromHash(hash);
      if (fromHash) {
        setTab(fromHash);
        return;
      }
      const next = resolveKnowledgeTab({ visibleTabIds: tabIds });
      setTab(next);
      if (next === "hivemind") {
        const hivemindNext = resolveKnowledgeHivemindSection({});
        setHivemindSection(hivemindNext);
        window.history.replaceState(null, "", knowledgeHivemindSectionHref(hivemindNext));
        return;
      }
      window.history.replaceState(null, "", knowledgeTabHref(next));
    };
    syncFromHash();
    window.addEventListener("hashchange", syncFromHash);
    return () => window.removeEventListener("hashchange", syncFromHash);
  }, [tabIds]);

  return (
    <HivePageShell
      title="Knowledge"
      subtitle="One plane — HiveMind retrieval, Ingest URL, outputs archive, recipes/learning, dreaming, curated memory, wiki layer, goals."
      hintKey="knowledge"
      banner={
        archiveSyncPending ? (
          <p className="rounded-xl border border-alert/30 bg-alert/10 px-4 py-3 text-sm text-(--qs-text-2) lg:hidden">
            Knowledge archive syncing — retrieval panels remain available.
          </p>
        ) : null
      }
      subnav={
        <HiveSectionSubnav
          primary={TABS.map(({ id, label, icon }) => ({ id, label, icon }))}
          secondary={
            tab === "hivemind"
              ? HIVEMIND_SECTIONS.map(({ id, label, icon }) => ({ id, label, icon }))
              : undefined
          }
          activePrimary={tab}
          activeSecondary={tab === "hivemind" ? hivemindSection : undefined}
          onPrimaryChange={(id) => selectTab(id as KnowledgeTab)}
          onSecondaryChange={(id) => selectHivemindSection(id as KnowledgeHivemindSection)}
          primaryAriaLabel="Knowledge sections"
          secondaryAriaLabel="HiveMind sub-sections"
          primaryMenuKey="knowledge-primary"
          secondaryMenuKey="knowledge-hivemind"
        />
      }
    >
      <HiveSubnavContent>
      {tab === "hivemind" && hivemindSection === "explorer" ? (
        <V4Card>
          <V4CardHeader
            kicker="Knowledge command center"
            title="Retrieval contract"
            description="Unified lens for retrieval: contract context, output archive, recipe / dreaming loops."
            hint={sectionHintNode("knowledgeRetrievalContract")}
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
              <p className="v4-knowledge-mono">wiki_only · deep_raw · default_v2</p>
              <p className="v4-knowledge-foot">Hot tier = curated + wiki. Cold tier = raw forager scrape (deep research).</p>
            </div>
            <div className="v4-knowledge-contract v4-knowledge-contract--gold">
              <span className="v4-label-kicker">Skill pack preset</span>
              <p className="v4-knowledge-mono v4-knowledge-mono--purple">context + decide + tdd + diagnose</p>
              <p className="v4-knowledge-foot">Active across Eval &amp; Action swarms.</p>
            </div>
          </div>
        </V4Card>
      ) : null}

      {tab === "hivemind" ? (
        <div id="hivemind" className="scroll-mt-28 space-y-6">
          {hivemindSection === "graphify" ? <AutoGraphifyPanel /> : null}
          {hivemindSection === "shape" ? <ProjectShapeGraphPanel /> : null}
          {hivemindSection === "recall" ? <SelectiveRecallPanel /> : null}
          {hivemindSection === "ingest" ? (
            <div id="research-bee" className="scroll-mt-28 space-y-3">
              {ingestError ? (
                <p className="rounded-xl border border-(--qs-red)/30 bg-(--qs-red)/10 px-4 py-3 text-sm">{ingestError}</p>
              ) : null}
              <ResearchBeePanel onError={setIngestError} />
            </div>
          ) : null}
          {hivemindSection === "explorer" ? (
            <V4Card>
              <V4CardHeader
                title="HiveMind · graph + vault + search"
                description="Neo4j semantic graph · ChromaDB vector fallback · retrieval-aware prompting."
                hint={sectionHintNode("knowledgeExplorer")}
                actions={
                  <div className="v4-hivemind-toolbar flex flex-wrap justify-start gap-2">
                    <Link href="/tasks/new" className="qs-btn qs-btn--ghost qs-btn--sm">
                      Quick ingest · task
                    </Link>
                    <Link href="/agents#sessions" className="qs-btn qs-btn--ghost qs-btn--sm">
                      Quick ingest · supervisor
                    </Link>
                  </div>
                }
              />
              <HiveMindExplorer
                showHeader={false}
                variant="v4"
                filterHint={filter}
                initialSearchQ={foragerSearchQ || (foragerId ? `forager:${foragerId}` : "")}
                autoSearchOnMount={Boolean(foragerId)}
              />
            </V4Card>
          ) : null}
          {hivemindSection === "evolution" ? <MemoryEvolutionPanel /> : null}
        </div>
      ) : null}

      {tab === "outputs" ? (
        <V4Card id="outputs" className="scroll-mt-28">
          <V4CardHeader
            title="Outputs &amp; archive"
            description="Semantic archive search · regenerate · PDF / markdown export in one operator loop."
            hint={sectionHintNode("knowledgeOutputs")}
          />
          <OutputsInteractivePanel initialItems={initialOutputs} />
        </V4Card>
      ) : null}

      {tab === "recipes" ? (
        <div id="recipes" className="scroll-mt-28 space-y-6">
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

      {tab === "dreaming" ? (
        <div id="dreaming" className="scroll-mt-28">
          <DreamingConsole />
        </div>
      ) : null}

      {tab === "memory" ? (
        <div id="memory" className="scroll-mt-28 space-y-6">
          <OperatorBrainPackPanel />
          <HiveSessionSearchPanel />
          <EpisodicMemoryPanel />
        </div>
      ) : null}

      {tab === "wiki" ? (
        <div id="wiki" className="scroll-mt-28">
          <WikiLayerPanel />
        </div>
      ) : null}

      {tab === "goals" ? (
        <div id="goals" className="scroll-mt-28">
          <GoalsPanel />
        </div>
      ) : null}
      </HiveSubnavContent>
    </HivePageShell>
  );
}
