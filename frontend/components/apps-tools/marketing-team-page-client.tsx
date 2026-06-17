"use client";

import { BarChart3, CalendarDays, Clapperboard, ListChecks, Palette, Rocket, Send } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HiveSubnavRow } from "@/components/hive/hive-subnav-row";
import { ModulePolicyPackPill } from "@/components/apps-tools/module-policy-pack-pill";
import { integrationsHubOAuthHref } from "@/lib/integrations-routes";
import { scrollBehaviorForMotion } from "@/lib/motion-preferences";

const MarketingTeamCalendarPanel = dynamic(
  () =>
    import("@/components/apps-tools/marketing-team-calendar-panel").then((mod) => ({
      default: mod.MarketingTeamCalendarPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[10rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioPublishQueuePanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-publish-queue-panel").then((mod) => ({
      default: mod.ExecutionStudioPublishQueuePanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[10rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioSocialPublishPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-social-publish-panel").then((mod) => ({
      default: mod.ExecutionStudioSocialPublishPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[10rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioPublishPerformancePanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-publish-performance-panel").then((mod) => ({
      default: mod.ExecutionStudioPublishPerformancePanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[10rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const CampaignLaunchWizardPanel = dynamic(
  () =>
    import("@/components/apps-tools/campaign-launch-wizard-panel").then((mod) => ({
      default: mod.CampaignLaunchWizardPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[10rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const FacelessStudioPanel = dynamic(
  () =>
    import("@/components/apps-tools/faceless-studio-panel").then((mod) => ({
      default: mod.FacelessStudioPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[10rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const BrandStudioPanel = dynamic(
  () =>
    import("@/components/apps-tools/brand-studio-panel").then((mod) => ({
      default: mod.BrandStudioPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[10rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

type MarketingTeamSection = "calendar" | "studio" | "brand" | "queue" | "publish" | "performance" | "launch";

const SECTION_TO_HASH: Record<MarketingTeamSection, string> = {
  calendar: "marketing-calendar",
  studio: "faceless-studio",
  brand: "brand-studio",
  launch: "campaign-launch-wizard",
  queue: "publish-queue",
  publish: "social-publish",
  performance: "publish-performance",
};

function sectionFromHash(hash: string): MarketingTeamSection | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (key === "marketing-calendar") return "calendar";
  if (key === "faceless-studio") return "studio";
  if (key === "brand-studio") return "brand";
  if (key === "campaign-launch-wizard") return "launch";
  if (key === "publish-queue") return "queue";
  if (key === "social-publish") return "publish";
  if (key === "publish-performance") return "performance";
  return null;
}

function sectionFromQuery(raw: string | null): MarketingTeamSection | null {
  if (
    raw === "calendar" ||
    raw === "studio" ||
    raw === "brand" ||
    raw === "launch" ||
    raw === "queue" ||
    raw === "publish" ||
    raw === "performance"
  ) {
    return raw;
  }
  return null;
}

export function MarketingTeamPageClient() {
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [section, setSection] = useState<MarketingTeamSection>("calendar");

  const updateUrl = useCallback((next: MarketingTeamSection) => {
    const hash = SECTION_TO_HASH[next];
    window.history.replaceState(null, "", `/apps-tools/marketing-team?section=${next}#${hash}`);
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
      title="Marketing Team"
      subtitle="Unified calendar, publish queue, and social distribution — simulate-first, post-bridge style."
      status={<ModulePolicyPackPill moduleKey="marketing_automation" />}
      error={error ? { message: error, onDismiss: () => setError(null) } : null}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link href={integrationsHubOAuthHref()} className="qs-btn qs-btn--ghost qs-btn--sm">
            Connect OAuth
          </Link>
          <Link href="/agents?preset=faceless-video#sessions" className="qs-btn qs-btn--ghost qs-btn--sm">
            Faceless agent session
          </Link>
        </div>
      }
      subnav={
        <HiveSubnavRow
          items={[
            { id: "calendar", label: "Calendar", icon: CalendarDays },
            { id: "studio", label: "Faceless studio", icon: Clapperboard },
            { id: "brand", label: "Brand studio", icon: Palette },
            { id: "queue", label: "Publish queue", icon: ListChecks },
            { id: "publish", label: "Social publish", icon: Send },
            { id: "performance", label: "Performance", icon: BarChart3 },
            { id: "launch", label: "Campaign launch", icon: Rocket },
          ]}
          activeId={section}
          onChange={(id) => {
            const next = id as MarketingTeamSection;
            setSection(next);
            updateUrl(next);
          }}
          ariaLabel="Marketing Team sections"
          menuKey="apps-tools-marketing-team"
        />
      }
    >
      <div id="marketing-calendar" className={section === "calendar" ? "" : "hidden"} aria-hidden={section !== "calendar"}>
        {section === "calendar" ? <MarketingTeamCalendarPanel /> : null}
      </div>
      <div id="faceless-studio" className={section === "studio" ? "" : "hidden"} aria-hidden={section !== "studio"}>
        {section === "studio" ? <FacelessStudioPanel /> : null}
      </div>
      <div id="brand-studio" className={section === "brand" ? "" : "hidden"} aria-hidden={section !== "brand"}>
        {section === "brand" ? <BrandStudioPanel /> : null}
      </div>
      <div id="campaign-launch-wizard" className={section === "launch" ? "" : "hidden"}>
        {section === "launch" ? <CampaignLaunchWizardPanel /> : null}
      </div>
      <div id="publish-queue" className={section === "queue" ? "" : "hidden"}>
        {section === "queue" ? <ExecutionStudioPublishQueuePanel onError={setError} /> : null}
      </div>
      <div id="publish-performance" className={section === "performance" ? "" : "hidden"}>
        {section === "performance" ? <ExecutionStudioPublishPerformancePanel onError={setError} /> : null}
      </div>
      <div id="social-publish" className={section === "publish" ? "" : "hidden"}>
        {section === "publish" ? <ExecutionStudioSocialPublishPanel onError={setError} /> : null}
      </div>
    </HivePageShell>
  );
}
