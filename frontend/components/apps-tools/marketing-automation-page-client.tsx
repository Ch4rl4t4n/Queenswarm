"use client";

import { BarChart3, ListChecks, Send } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HiveSubnavRow } from "@/components/hive/hive-subnav-row";
import { ModulePolicyPackPill } from "@/components/apps-tools/module-policy-pack-pill";
import { integrationsHubOAuthHref } from "@/lib/integrations-routes";
import { scrollBehaviorForMotion } from "@/lib/motion-preferences";

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

type MarketingSection = "queue" | "publish" | "performance";

const SECTION_TO_HASH: Record<MarketingSection, string> = {
  queue: "publish-queue",
  publish: "social-publish",
  performance: "publish-performance",
};

function sectionFromHash(hash: string): MarketingSection | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (key === "publish-queue") return "queue";
  if (key === "social-publish") return "publish";
  if (key === "publish-performance") return "performance";
  return null;
}

function sectionFromQuery(raw: string | null): MarketingSection | null {
  if (raw === "queue" || raw === "publish" || raw === "performance") {
    return raw;
  }
  return null;
}

export function MarketingAutomationPageClient() {
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [section, setSection] = useState<MarketingSection>("publish");

  const updateUrl = useCallback((next: MarketingSection) => {
    const hash = SECTION_TO_HASH[next];
    window.history.replaceState(null, "", `/apps-tools/marketing-automation?section=${next}#${hash}`);
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
      title="Marketing Automation"
      subtitle="Dedicated workspace for publish queue governance, social distribution, and performance feedback."
      status={<ModulePolicyPackPill moduleKey="marketing_automation" />}
      error={error ? { message: error, onDismiss: () => setError(null) } : null}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link href={integrationsHubOAuthHref()} className="qs-btn qs-btn--primary qs-btn--sm">
            Connect social accounts
          </Link>
          <Link href="/integrations?tab=studio&section=publish#social-publish" className="qs-btn qs-btn--ghost qs-btn--sm">
            Open legacy studio view
          </Link>
        </div>
      }
      subnav={
        <HiveSubnavRow
          items={[
            { id: "queue", label: "Publish queue", icon: ListChecks },
            { id: "publish", label: "Social publish", icon: Send },
            { id: "performance", label: "Performance", icon: BarChart3 },
          ]}
          activeId={section}
          onChange={(id) => {
            const next = id as MarketingSection;
            setSection(next);
            updateUrl(next);
          }}
          ariaLabel="Marketing automation sections"
          menuKey="apps-tools-marketing-automation"
        />
      }
    >
      {section === "queue" ? <ExecutionStudioPublishQueuePanel onError={setError} /> : null}
      {section === "publish" ? <ExecutionStudioSocialPublishPanel onError={setError} /> : null}
      {section === "performance" ? <ExecutionStudioPublishPerformancePanel onError={setError} /> : null}
    </HivePageShell>
  );
}
