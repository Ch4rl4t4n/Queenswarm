"use client";

import { BookOpen, Network, Sparkles } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HiveSubnavRow } from "@/components/hive/hive-subnav-row";
import { ResearchBeePanel } from "@/components/hive/research-bee-panel";
import { ModulePolicyPackPill } from "@/components/apps-tools/module-policy-pack-pill";
import { V4Card, V4CardHeader } from "@/components/ui/v4";
import { knowledgeHivemindSectionHref } from "@/lib/knowledge-hivemind-routes";
import { scrollBehaviorForMotion } from "@/lib/motion-preferences";

type ResearchSection = "briefing" | "hivemind" | "automation";

const SECTION_TO_HASH: Record<ResearchSection, string> = {
  briefing: "research-bee",
  hivemind: "hivemind-links",
  automation: "research-automation",
};

function sectionFromHash(hash: string): ResearchSection | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (key === "research-bee") return "briefing";
  if (key === "hivemind-links") return "hivemind";
  if (key === "research-automation") return "automation";
  return null;
}

function sectionFromQuery(raw: string | null): ResearchSection | null {
  if (raw === "briefing" || raw === "hivemind" || raw === "automation") {
    return raw;
  }
  return null;
}

export function ResearchWorkspacePageClient() {
  const searchParams = useSearchParams();
  const [section, setSection] = useState<ResearchSection>("briefing");
  const [error, setError] = useState<string | null>(null);

  const updateUrl = useCallback((next: ResearchSection) => {
    const hash = SECTION_TO_HASH[next];
    window.history.replaceState(null, "", `/apps-tools/research-workspace?section=${next}#${hash}`);
  }, []);

  useEffect(() => {
    const fromQuery = sectionFromQuery(searchParams.get("section"));
    const fromHash = sectionFromHash(typeof window !== "undefined" ? window.location.hash : "");
    const next = fromQuery ?? fromHash;
    if (next) {
      setSection(next);
    }
  }, [searchParams]);

  useEffect(() => {
    const target = document.getElementById(SECTION_TO_HASH[section]);
    if (target) {
      target.scrollIntoView({ behavior: scrollBehaviorForMotion(), block: "start" });
    }
  }, [section]);

  return (
    <HivePageShell
      title="Research Workspace"
      subtitle="Briefing-first research lane connected to HiveMind retrieval and swarm automation handoff."
      status={<ModulePolicyPackPill moduleKey="research_workspace" />}
      error={error ? { message: error, onDismiss: () => setError(null) } : null}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link href="/knowledge#hivemind" className="qs-btn qs-btn--ghost qs-btn--sm">
            Open HiveMind
          </Link>
          <Link href="/agentic-os#icm" className="qs-btn qs-btn--ghost qs-btn--sm">
            Open Agentic OS tools
          </Link>
        </div>
      }
      subnav={
        <HiveSubnavRow
          items={[
            { id: "briefing", label: "Research bee", icon: BookOpen },
            { id: "hivemind", label: "HiveMind recall", icon: Network },
            { id: "automation", label: "Automation handoff", icon: Sparkles },
          ]}
          activeId={section}
          onChange={(id) => {
            const next = id as ResearchSection;
            setSection(next);
            updateUrl(next);
          }}
          ariaLabel="Research workspace sections"
          menuKey="apps-tools-research-workspace"
        />
      }
    >
      {section === "briefing" ? <ResearchBeePanel onError={setError} /> : null}

      {section === "hivemind" ? (
        <V4Card id="hivemind-links">
          <V4CardHeader
            title="HiveMind recall surfaces"
            description="Use these lanes to validate, compare, and persist research outcomes before swarm execution."
          />
          <div className="grid gap-2">
            <Link className="qs-btn qs-btn--ghost qs-btn--sm justify-start" href={knowledgeHivemindSectionHref("explorer")}>
              Open semantic explorer
            </Link>
            <Link className="qs-btn qs-btn--ghost qs-btn--sm justify-start" href={knowledgeHivemindSectionHref("recall")}>
              Open selective recall
            </Link>
            <Link className="qs-btn qs-btn--ghost qs-btn--sm justify-start" href={knowledgeHivemindSectionHref("shape")}>
              Open project shape graph
            </Link>
            <Link className="qs-btn qs-btn--ghost qs-btn--sm justify-start" href={knowledgeHivemindSectionHref("graphify")}>
              Open auto-graphify
            </Link>
          </div>
        </V4Card>
      ) : null}

      {section === "automation" ? (
        <V4Card id="research-automation">
          <V4CardHeader
            title="Automation handoff"
            description="Bridge verified research into execution lanes without bypassing simulation and approvals."
          />
          <div className="grid gap-2">
            <Link className="qs-btn qs-btn--ghost qs-btn--sm justify-start" href="/apps-tools/marketing-automation">
              Handoff to Marketing Automation
            </Link>
            <Link className="qs-btn qs-btn--ghost qs-btn--sm justify-start" href="/apps-tools/trading-automation">
              Handoff to Trading Automation
            </Link>
            <Link className="qs-btn qs-btn--ghost qs-btn--sm justify-start" href="/apps-tools/browser-automation">
              Handoff to Browser Automation
            </Link>
          </div>
        </V4Card>
      ) : null}
    </HivePageShell>
  );
}
