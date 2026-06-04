"use client";

import { Building2, Factory, Package } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HiveSubnavRow } from "@/components/hive/hive-subnav-row";
import { ModulePolicyPackPill } from "@/components/apps-tools/module-policy-pack-pill";
import { scrollBehaviorForMotion } from "@/lib/motion-preferences";
import {
  FACTORY_BLUEPRINT_PATH,
  FACTORY_CROSS_LINK_LABELS,
} from "@/lib/factory-content-factory-routes";

const ExecutionStudioMediaAgencyPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-media-agency-panel").then((mod) => ({
      default: mod.ExecutionStudioMediaAgencyPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[10rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioMicroSaasFactoryPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-micro-saas-factory-panel").then((mod) => ({
      default: mod.ExecutionStudioMicroSaasFactoryPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[10rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

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

type ContentFactorySection = "agency" | "micro-saas" | "pack-factory";

const SECTION_TO_HASH: Record<ContentFactorySection, string> = {
  agency: "media-agency",
  "micro-saas": "micro-saas-factory",
  "pack-factory": "pack-factory",
};

function sectionFromHash(hash: string): ContentFactorySection | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (key === "media-agency") return "agency";
  if (key === "micro-saas-factory") return "micro-saas";
  if (key === "pack-factory") return "pack-factory";
  return null;
}

function sectionFromQuery(raw: string | null): ContentFactorySection | null {
  if (raw === "agency" || raw === "micro-saas" || raw === "pack-factory") {
    return raw;
  }
  return null;
}

export function ContentFactoryPageClient() {
  const searchParams = useSearchParams();
  const [section, setSection] = useState<ContentFactorySection>("agency");
  const [error, setError] = useState<string | null>(null);

  const updateUrl = useCallback((next: ContentFactorySection) => {
    const hash = SECTION_TO_HASH[next];
    window.history.replaceState(null, "", `/apps-tools/content-factory?section=${next}#${hash}`);
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
      title="Content Factory"
      subtitle="Content production module for white-label media operations and Micro-SaaS launch workflows."
      status={<ModulePolicyPackPill moduleKey="content_factory" />}
      error={error ? { message: error, onDismiss: () => setError(null) } : null}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link href="/integrations?tab=studio&section=lanes#media-agency" className="qs-btn qs-btn--ghost qs-btn--sm">
            Open legacy studio lane
          </Link>
          <Link href={FACTORY_BLUEPRINT_PATH} className="qs-btn qs-btn--ghost qs-btn--sm">
            {FACTORY_CROSS_LINK_LABELS.toBlueprint}
          </Link>
        </div>
      }
      subnav={
        <HiveSubnavRow
          items={[
            { id: "agency", label: "Media agency", icon: Building2 },
            { id: "micro-saas", label: "Micro-SaaS factory", icon: Factory },
            { id: "pack-factory", label: "Pack factory", icon: Package },
          ]}
          activeId={section}
          onChange={(id) => {
            const next = id as ContentFactorySection;
            setSection(next);
            updateUrl(next);
          }}
          ariaLabel="Content factory sections"
          menuKey="apps-tools-content-factory"
        />
      }
    >
      {section === "agency" ? <ExecutionStudioMediaAgencyPanel onError={setError} /> : null}
      {section === "micro-saas" ? <ExecutionStudioMicroSaasFactoryPanel onError={setError} /> : null}
      {section === "pack-factory" ? <ContentPackFactoryPanel onError={setError} /> : null}
    </HivePageShell>
  );
}
