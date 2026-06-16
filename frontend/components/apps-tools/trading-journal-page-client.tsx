"use client";

import { Brain, Clock3, Moon, NotebookPen, Settings2 } from "lucide-react";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";

import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HiveSubnavRow } from "@/components/hive/hive-subnav-row";
import { ModulePolicyPackPill } from "@/components/apps-tools/module-policy-pack-pill";
import { scrollBehaviorForMotion } from "@/lib/motion-preferences";

const JournalStudioEntriesPanel = dynamic(
  () =>
    import("@/components/apps-tools/journal-studio-entries-panel").then((mod) => ({
      default: mod.JournalStudioEntriesPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const JournalStudioTimelinePanel = dynamic(
  () =>
    import("@/components/apps-tools/journal-studio-timeline-panel").then((mod) => ({
      default: mod.JournalStudioTimelinePanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const JournalStudioGardenerPanel = dynamic(
  () =>
    import("@/components/apps-tools/journal-studio-gardener-panel").then((mod) => ({
      default: mod.JournalStudioGardenerPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const JournalStudioSettingsPanel = dynamic(
  () =>
    import("@/components/apps-tools/journal-studio-settings-panel").then((mod) => ({
      default: mod.JournalStudioSettingsPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const JournalStudioPretradeRecallPanel = dynamic(
  () =>
    import("@/components/apps-tools/journal-studio-pretrade-recall-panel").then((mod) => ({
      default: mod.JournalStudioPretradeRecallPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

type JournalSection = "timeline" | "entries" | "gardener" | "recall" | "settings";

const SECTION_TO_HASH: Record<JournalSection, string> = {
  timeline: "journal-studio-timeline",
  entries: "journal-studio-entries",
  gardener: "journal-studio-gardener",
  recall: "journal-studio-pretrade-recall",
  settings: "journal-studio-settings",
};

function sectionFromHash(hash: string): JournalSection | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (key === "journal-studio-timeline") return "timeline";
  if (key === "journal-studio-entries") return "entries";
  if (key === "journal-studio-gardener") return "gardener";
  if (key === "journal-studio-pretrade-recall") return "recall";
  if (key === "journal-studio-settings") return "settings";
  return null;
}

function sectionFromQuery(raw: string | null): JournalSection | null {
  if (raw === "timeline") return "timeline";
  if (raw === "entries") return "entries";
  if (raw === "gardener") return "gardener";
  if (raw === "recall") return "recall";
  if (raw === "settings") return "settings";
  return null;
}

export function TradingJournalPageClient(): JSX.Element {
  const [section, setSection] = useState<JournalSection>("timeline");

  useEffect(() => {
    const hashSection = sectionFromHash(window.location.hash);
    const params = new URLSearchParams(window.location.search);
    const querySection = sectionFromQuery(params.get("section"));
    setSection(hashSection ?? querySection ?? "timeline");
  }, []);

  const updateUrl = useCallback((next: JournalSection) => {
    const hash = SECTION_TO_HASH[next];
    window.history.replaceState(null, "", `/apps-tools/trading-journal?section=${next}#${hash}`);
  }, []);

  useEffect(() => {
    const target = document.getElementById(SECTION_TO_HASH[section]);
    if (target) {
      target.scrollIntoView({ behavior: scrollBehaviorForMotion(), block: "start" });
    }
  }, [section]);

  return (
    <HivePageShell
      title="Trading Journal"
      subtitle="Learning Loop Studio — timeline, entries, gardener, pre-trade recall, review cron, Obsidian vault."
      status={<ModulePolicyPackPill moduleKey="trading_journal" />}
      subnav={
        <HiveSubnavRow
          items={[
            { id: "timeline", label: "Timeline", icon: Clock3 },
            { id: "entries", label: "Trade entries", icon: NotebookPen },
            { id: "gardener", label: "Gardener", icon: Moon },
            { id: "recall", label: "Pre-trade recall", icon: Brain },
            { id: "settings", label: "Studio settings", icon: Settings2 },
          ]}
          activeId={section}
          onChange={(id) => {
            const next = id as JournalSection;
            setSection(next);
            updateUrl(next);
          }}
          ariaLabel="Trading journal sections"
          menuKey="apps-tools-trading-journal"
        />
      }
    >
      {section === "timeline" ? <JournalStudioTimelinePanel /> : null}
      {section === "entries" ? <JournalStudioEntriesPanel /> : null}
      {section === "gardener" ? <JournalStudioGardenerPanel /> : null}
      {section === "recall" ? <JournalStudioPretradeRecallPanel /> : null}
      {section === "settings" ? <JournalStudioSettingsPanel /> : null}
    </HivePageShell>
  );
}
