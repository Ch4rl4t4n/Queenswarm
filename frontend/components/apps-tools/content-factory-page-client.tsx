"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { BookOpenIcon, RefreshCwIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { useSkillFactoryNav } from "@/components/apps-tools/skill-factory-nav-context";
import { ModulePolicyPackPill } from "@/components/apps-tools/module-policy-pack-pill";
import {
  navigateContentPackFactoryTab,
  resolveContentPackFactoryTab,
  type ContentPackFactoryTab,
} from "@/lib/apps-tools-routes";
import { FACTORY_BLUEPRINT_PATH, FACTORY_CROSS_LINK_LABELS } from "@/lib/factory-content-factory-routes";
import { useRouteHash } from "@/lib/hooks/use-route-hash";
import { MANUAL_HREFS } from "@/lib/manual-routes";

const ContentPackFactoryPanel = dynamic(
  () =>
    import("@/components/apps-tools/content-pack-factory-panel").then((mod) => ({
      default: mod.ContentPackFactoryPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[10rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

/** Content Pack Factory — embedded in Apps & Tools shell (same nav pattern as Skill Factory). */
export function ContentFactoryPageClient(): JSX.Element {
  const routeHash = useRouteHash();
  const { setPackQueueBadge } = useSkillFactoryNav();
  const tab = useMemo(() => resolveContentPackFactoryTab({ hash: routeHash }), [routeHash]);
  const [error, setError] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    if (!routeHash && typeof window !== "undefined") {
      navigateContentPackFactoryTab("pipeline");
    }
  }, [routeHash]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const legacySection = params.get("section");
    if (legacySection === "pack-factory" || legacySection === "pipeline") {
      navigateContentPackFactoryTab("pipeline");
    }
  }, []);

  const onQueueCountChange = useCallback(
    (count: number | undefined) => {
      setPackQueueBadge(count);
    },
    [setPackQueueBadge],
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-(--qs-text)">Content Pack Factory</p>
            <ModulePolicyPackPill moduleKey="content_factory" />
          </div>
          <p className="mt-0.5 text-xs text-(--qs-text-3)">
            Niche content harness packs — same eval + Gumroad export lane as Skill Factory.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/apps-tools/skill-factory#launch" className="qs-btn qs-btn--ghost qs-btn--sm">
            Skill Factory Launch
          </Link>
          <Link href={FACTORY_BLUEPRINT_PATH} className="qs-btn qs-btn--ghost qs-btn--sm">
            {FACTORY_CROSS_LINK_LABELS.toBlueprint}
          </Link>
          <Link href={MANUAL_HREFS.manualContentPackFactory} className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5">
            <BookOpenIcon className="size-3.5" aria-hidden />
            Manual
          </Link>
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
            onClick={() => setRefreshToken((value) => value + 1)}
          >
            <RefreshCwIcon className="size-3.5" aria-hidden />
            Refresh
          </button>
          <Link href={MANUAL_HREFS.settingsLlmKeys} className="qs-btn qs-btn--ghost qs-btn--sm">
            LLM keys
          </Link>
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-(--qs-error)/40 bg-(--qs-error)/10 px-4 py-3 text-sm text-(--qs-error)">
          <div className="flex items-start justify-between gap-3">
            <p>{error}</p>
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => setError(null)}>
              Dismiss
            </button>
          </div>
        </div>
      ) : null}

      <ContentPackFactoryPanel
        activeTab={tab}
        refreshToken={refreshToken}
        onError={setError}
        onQueueCountChange={onQueueCountChange}
      />

      <details className="rounded-xl border border-white/10 bg-black/20 p-4 text-xs text-(--qs-text-3)">
        <summary className="cursor-pointer font-medium text-(--qs-text-2)">Legacy lanes (frozen)</summary>
        <p className="mt-2">
          Media agency and Micro-SaaS factory are deprioritized. Use{" "}
          <Link href="/integrations?tab=studio&section=lanes#media-agency" className="text-cyan underline">
            Integrations → Studio
          </Link>{" "}
          if needed.
        </p>
      </details>
    </div>
  );
}
