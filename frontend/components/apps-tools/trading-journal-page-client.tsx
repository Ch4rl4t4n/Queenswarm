"use client";

import { BookMarked, Settings2 } from "lucide-react";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";

import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HiveSubnavRow } from "@/components/hive/hive-subnav-row";
import { ModulePolicyPackPill } from "@/components/apps-tools/module-policy-pack-pill";
import { scrollBehaviorForMotion } from "@/lib/motion-preferences";

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

type JournalSection = "settings";

const SECTION_TO_HASH: Record<JournalSection, string> = {
  settings: "journal-studio-settings",
};

function sectionFromHash(hash: string): JournalSection | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (key === "journal-studio-settings") return "settings";
  return null;
}

function sectionFromQuery(raw: string | null): JournalSection | null {
  if (raw === "settings") return "settings";
  return null;
}

export function TradingJournalPageClient(): JSX.Element {
  const [section, setSection] = useState<JournalSection>("settings");

  useEffect(() => {
    const hashSection = sectionFromHash(window.location.hash);
    const params = new URLSearchParams(window.location.search);
    const querySection = sectionFromQuery(params.get("section"));
    setSection(hashSection ?? querySection ?? "settings");
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
      subtitle="Learning Loop Studio — journal fields, review cron, Obsidian vault, mistake recall."
      status={<ModulePolicyPackPill moduleKey="trading_journal" />}
      subnav={
        <HiveSubnavRow
          items={[{ id: "settings", label: "Studio settings", icon: Settings2 }]}
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
      {section === "settings" ? <JournalStudioSettingsPanel /> : null}
    </HivePageShell>
  );
}
