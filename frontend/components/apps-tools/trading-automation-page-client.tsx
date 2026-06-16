"use client";

import { Activity, Shield, ShieldAlert, TrendingUp } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HiveSubnavRow } from "@/components/hive/hive-subnav-row";
import { ModulePolicyPackPill } from "@/components/apps-tools/module-policy-pack-pill";
import { scrollBehaviorForMotion } from "@/lib/motion-preferences";

const TradingThesisWizardPanel = dynamic(
  () =>
    import("@/components/connectors/trading-thesis-wizard-panel").then((mod) => ({
      default: mod.TradingThesisWizardPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[6rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioTradingCockpitPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-trading-cockpit-panel").then((mod) => ({
      default: mod.ExecutionStudioTradingCockpitPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[10rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioTradingContentHybridPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-trading-content-hybrid-panel").then((mod) => ({
      default: mod.ExecutionStudioTradingContentHybridPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[10rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const BrokerGuardrailsPanel = dynamic(
  () =>
    import("@/components/connectors/broker-guardrails-panel").then((mod) => ({
      default: mod.BrokerGuardrailsPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioLiveLanePanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-live-lane-panel").then((mod) => ({
      default: mod.ExecutionStudioLiveLanePanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[10rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

type TradingSection = "cockpit" | "guardrails" | "hybrid" | "live-lane";

const SECTION_TO_HASH: Record<TradingSection, string> = {
  cockpit: "trading-cockpit",
  guardrails: "broker-guardrails",
  hybrid: "trading-content-hybrid",
  "live-lane": "live-lane",
};

function sectionFromHash(hash: string): TradingSection | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (key === "trading-cockpit") return "cockpit";
  if (key === "broker-guardrails") return "guardrails";
  if (key === "trading-content-hybrid") return "hybrid";
  if (key === "live-lane") return "live-lane";
  return null;
}

function sectionFromQuery(raw: string | null): TradingSection | null {
  if (raw === "cockpit" || raw === "guardrails" || raw === "hybrid" || raw === "live-lane") {
    return raw;
  }
  return null;
}

export function TradingAutomationPageClient() {
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [section, setSection] = useState<TradingSection>(
    () => sectionFromQuery(searchParams.get("section")) ?? "cockpit",
  );

  const updateUrl = useCallback((next: TradingSection) => {
    const hash = SECTION_TO_HASH[next];
    window.history.replaceState(null, "", `/apps-tools/trading-automation?section=${next}#${hash}`);
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
      title="Trading Automation"
      subtitle="Trading cockpit, trade-to-content hybrid intelligence, and live-lane readiness in one guarded workspace."
      status={<ModulePolicyPackPill moduleKey="trading_automation" />}
      error={error ? { message: error, onDismiss: () => setError(null) } : null}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link href="/integrations?tab=studio&section=publish#trading-cockpit" className="qs-btn qs-btn--ghost qs-btn--sm">
            Open legacy studio view
          </Link>
          <Link href="/integrations?tab=studio&section=lanes#live-lane" className="qs-btn qs-btn--ghost qs-btn--sm">
            Open live-lane prep
          </Link>
        </div>
      }
      subnav={
        <HiveSubnavRow
          items={[
            { id: "cockpit", label: "Trading cockpit", icon: TrendingUp },
            { id: "guardrails", label: "Broker guardrails", icon: Shield },
            { id: "hybrid", label: "Hybrid loop", icon: Activity },
            { id: "live-lane", label: "Live lane prep", icon: ShieldAlert },
          ]}
          activeId={section}
          onChange={(id) => {
            const next = id as TradingSection;
            setSection(next);
            updateUrl(next);
          }}
          ariaLabel="Trading automation sections"
          menuKey="apps-tools-trading-automation"
        />
      }
    >
      {section === "cockpit" ? (
        <>
          <TradingThesisWizardPanel />
          <ExecutionStudioTradingCockpitPanel onError={setError} />
        </>
      ) : null}
      {section === "guardrails" ? <BrokerGuardrailsPanel /> : null}
      {section === "hybrid" ? <ExecutionStudioTradingContentHybridPanel onError={setError} /> : null}
      {section === "live-lane" ? <ExecutionStudioLiveLanePanel onError={setError} /> : null}
    </HivePageShell>
  );
}
