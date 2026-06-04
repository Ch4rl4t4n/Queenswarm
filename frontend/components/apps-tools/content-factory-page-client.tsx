"use client";

import { Package } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HiveSubnavRow } from "@/components/hive/hive-subnav-row";
import { ModulePolicyPackPill } from "@/components/apps-tools/module-policy-pack-pill";
import { scrollBehaviorForMotion } from "@/lib/motion-preferences";
import { FACTORY_BLUEPRINT_PATH, FACTORY_CROSS_LINK_LABELS } from "@/lib/factory-content-factory-routes";

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

type ContentFactorySection = "pack-factory";

const SECTION_TO_HASH: Record<ContentFactorySection, string> = {
  "pack-factory": "pack-factory",
};

function sectionFromHash(hash: string): ContentFactorySection | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (key === "pack-factory") return "pack-factory";
  return null;
}

function sectionFromQuery(raw: string | null): ContentFactorySection | null {
  if (raw === "pack-factory") return "pack-factory";
  return null;
}

export function ContentFactoryPageClient() {
  const searchParams = useSearchParams();
  const [section, setSection] = useState<ContentFactorySection>("pack-factory");
  const [error, setError] = useState<string | null>(null);

  const updateUrl = useCallback((next: ContentFactorySection) => {
    const hash = SECTION_TO_HASH[next];
    window.history.replaceState(null, "", `/apps-tools/content-factory?section=${next}#${hash}`);
  }, []);

  useEffect(() => {
    const fromQuery = sectionFromQuery(searchParams.get("section"));
    const fromHash = sectionFromHash(typeof window !== "undefined" ? window.location.hash : "");
    const next = fromQuery ?? fromHash ?? "pack-factory";
    setSection(next);
    if (!fromQuery && !fromHash) {
      updateUrl("pack-factory");
    }
  }, [searchParams, updateUrl]);

  useEffect(() => {
    const target = document.getElementById(SECTION_TO_HASH[section]);
    if (target) {
      target.scrollIntoView({ behavior: scrollBehaviorForMotion(), block: "start" });
    }
  }, [section]);

  return (
    <HivePageShell
      title="Content Pack Factory"
      subtitle="Niche content harness packs — same eval + Gumroad export lane as Skill Factory."
      status={<ModulePolicyPackPill moduleKey="content_factory" />}
      error={error ? { message: error, onDismiss: () => setError(null) } : null}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link href="/apps-tools/skill-factory#launch" className="qs-btn qs-btn--ghost qs-btn--sm">
            Skill Factory Launch
          </Link>
          <Link href={FACTORY_BLUEPRINT_PATH} className="qs-btn qs-btn--ghost qs-btn--sm">
            {FACTORY_CROSS_LINK_LABELS.toBlueprint}
          </Link>
        </div>
      }
      subnav={
        <HiveSubnavRow
          items={[{ id: "pack-factory", label: "Pack factory", icon: Package }]}
          activeId={section}
          onChange={() => {
            setSection("pack-factory");
            updateUrl("pack-factory");
          }}
          ariaLabel="Content pack factory"
          menuKey="apps-tools-content-factory"
        />
      }
    >
      <ContentPackFactoryPanel onError={setError} />
      <details className="mt-6 rounded-xl border border-white/10 bg-black/20 p-4 text-xs text-(--qs-text-3)">
        <summary className="cursor-pointer font-medium text-(--qs-text-2)">Legacy lanes (frozen)</summary>
        <p className="mt-2">
          Media agency and Micro-SaaS factory are deprioritized. Use{" "}
          <Link href="/integrations?tab=studio&section=lanes#media-agency" className="text-cyan underline">
            Integrations → Studio
          </Link>{" "}
          if needed.
        </p>
      </details>
    </HivePageShell>
  );
}
