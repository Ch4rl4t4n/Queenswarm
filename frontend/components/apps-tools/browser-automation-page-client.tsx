"use client";

import { Compass, ShieldCheck, Wrench } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { HiveSubnavRow } from "@/components/hive/hive-subnav-row";
import { ModulePolicyPackPill } from "@/components/apps-tools/module-policy-pack-pill";
import { HiveApiError, hiveGet } from "@/lib/api";
import type { BrowserFallbackLane, PendingApprovalsSnapshot } from "@/lib/execution-studio-shared-types";
import { scrollBehaviorForMotion } from "@/lib/motion-preferences";

const ExecutionStudioLiveApprovalsPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-live-approvals-panel").then((mod) => ({
      default: mod.ExecutionStudioLiveApprovalsPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[10rem] animate-pulse bg-white/5 p-4" aria-hidden />,
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

const ExecutionStudioInnovationPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-innovation-panel").then((mod) => ({
      default: mod.ExecutionStudioInnovationPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[10rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

interface BrowserAutomationOverview {
  policy: {
    default_mode: "draft" | "simulate" | "live";
    live_requires_approval: boolean;
  };
  pending_approvals?: PendingApprovalsSnapshot;
  browser_fallback?: BrowserFallbackLane;
}

type BrowserSection = "approvals" | "live-lane" | "innovation";

const SECTION_TO_HASH: Record<BrowserSection, string> = {
  approvals: "studio-pending-live",
  "live-lane": "live-lane",
  innovation: "innovation-lab",
};

function sectionFromHash(hash: string): BrowserSection | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (key === "studio-pending-live") return "approvals";
  if (key === "live-lane") return "live-lane";
  if (key === "innovation-lab") return "innovation";
  return null;
}

function sectionFromQuery(raw: string | null): BrowserSection | null {
  if (raw === "approvals" || raw === "live-lane" || raw === "innovation") {
    return raw;
  }
  return null;
}

export function BrowserAutomationPageClient() {
  const searchParams = useSearchParams();
  const [section, setSection] = useState<BrowserSection>("approvals");
  const [error, setError] = useState<string | null>(null);
  const [executeResult, setExecuteResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<BrowserAutomationOverview | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await hiveGet<BrowserAutomationOverview>("execution-studio/overview");
      setOverview(data);
    } catch (exc) {
      setError(exc instanceof HiveApiError ? exc.message : "Failed to load browser automation workspace.");
    } finally {
      setLoading(false);
    }
  }, []);

  const updateUrl = useCallback((next: BrowserSection) => {
    const hash = SECTION_TO_HASH[next];
    window.history.replaceState(null, "", `/apps-tools/browser-automation?section=${next}#${hash}`);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

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
      title="Browser Automation"
      subtitle="Operator-approved browser harness lane with live confirmations, fallback checks, and innovation handoff."
      status={
        <div className="hidden items-center gap-2 lg:flex">
          <ModulePolicyPackPill moduleKey="browser_automation" />
          <HiveRefreshButton busy={loading} onClick={() => void load()} />
        </div>
      }
      error={error ? { message: error, onDismiss: () => setError(null) } : null}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link href="/integrations?tab=studio&section=lanes#live-lane" className="qs-btn qs-btn--ghost qs-btn--sm">
            Open legacy studio lane
          </Link>
          <Link href="/integrations?tab=hub&hubSection=roster" className="qs-btn qs-btn--primary qs-btn--sm">
            Manage connectors
          </Link>
        </div>
      }
      subnav={
        <HiveSubnavRow
          items={[
            { id: "approvals", label: "Live approvals", icon: ShieldCheck },
            { id: "live-lane", label: "Lane readiness", icon: Compass },
            { id: "innovation", label: "Innovation", icon: Wrench },
          ]}
          activeId={section}
          onChange={(id) => {
            const next = id as BrowserSection;
            setSection(next);
            updateUrl(next);
          }}
          ariaLabel="Browser automation sections"
          menuKey="apps-tools-browser-automation"
        />
      }
    >
      {executeResult ? (
        <div className="rounded-xl border border-cyan/30 bg-cyan/10 px-3 py-2 text-xs text-cyan">{executeResult}</div>
      ) : null}

      {section === "approvals" ? (
        <ExecutionStudioLiveApprovalsPanel
          pendingApprovals={overview?.pending_approvals}
          browserFallback={overview?.browser_fallback}
          defaultMode={overview?.policy.default_mode ?? "simulate"}
          liveRequiresApproval={overview?.policy.live_requires_approval ?? true}
          loading={loading}
          onPendingApprovalsUpdate={(pending) =>
            setOverview((prev) => (prev ? { ...prev, pending_approvals: pending } : prev))
          }
          onError={setError}
          onExecuteResult={setExecuteResult}
          onReloadOverview={load}
        />
      ) : null}

      {section === "live-lane" ? <ExecutionStudioLiveLanePanel onError={setError} /> : null}
      {section === "innovation" ? <ExecutionStudioInnovationPanel /> : null}
    </HivePageShell>
  );
}
