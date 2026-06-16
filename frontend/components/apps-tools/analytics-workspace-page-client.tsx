"use client";

import { BarChart3, CircleHelp, Download, FileText, GitBranch, LayoutDashboard, Loader2Icon, Plug } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AnalyticsConnectorProfilePanel } from "@/components/apps-tools/analytics-connector-profile-panel";
import { AnalyticsDataLineagePanel } from "@/components/apps-tools/analytics-data-lineage-panel";
import { AnalyticsReportArtifactPanel } from "@/components/apps-tools/analytics-report-artifact-panel";
import { BusinessQuestionWizardPanel } from "@/components/apps-tools/business-question-wizard-panel";
import { ModulePolicyPackPill } from "@/components/apps-tools/module-policy-pack-pill";
import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HiveSubnavRow } from "@/components/hive/hive-subnav-row";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { scrollBehaviorForMotion } from "@/lib/motion-preferences";

type AnalyticsSection = "overview" | "connectors" | "question" | "report" | "lineage" | "export";

interface AnalyticsSnapshot {
  enabled: boolean;
  capability_key: string;
  template_id: string;
  skill_slugs: string[];
  swarm_template_built: boolean;
  panels: Array<{ id: string; label: string; lazy: boolean; status: string }>;
  connector_slots: Array<{ id: string; label: string; ready: boolean; mode: string; detail: string }>;
  actions: Array<{ id: string; label: string; href: string; detail: string }>;
  operator_hint: string;
}

const SECTION_TO_HASH: Record<AnalyticsSection, string> = {
  overview: "analytics-overview",
  connectors: "analytics-connectors",
  question: "analytics-question",
  report: "analytics-report",
  lineage: "analytics-lineage",
  export: "analytics-export",
};

function sectionFromQuery(raw: string | null): AnalyticsSection | null {
  if (
    raw === "overview" ||
    raw === "connectors" ||
    raw === "question" ||
    raw === "report" ||
    raw === "lineage" ||
    raw === "export"
  ) {
    return raw;
  }
  return null;
}

function sectionFromHash(hash: string): AnalyticsSection | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (key === "analytics-overview") return "overview";
  if (key === "analytics-connectors") return "connectors";
  if (key === "analytics-question") return "question";
  if (key === "analytics-report") return "report";
  if (key === "analytics-lineage") return "lineage";
  if (key === "analytics-export") return "export";
  return null;
}

export function AnalyticsWorkspacePageClient(): JSX.Element {
  const searchParams = useSearchParams();
  const [section, setSection] = useState<AnalyticsSection>("overview");
  const [snapshot, setSnapshot] = useState<AnalyticsSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const updateUrl = useCallback((next: AnalyticsSection) => {
    const hash = SECTION_TO_HASH[next];
    window.history.replaceState(null, "", `/apps-tools/analytics?section=${next}#${hash}`);
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
    let active = true;
    const load = async (): Promise<void> => {
      setLoading(true);
      try {
        const body = await hiveGet<AnalyticsSnapshot>("analytics-workspace/snapshot");
        if (!active) return;
        setSnapshot(body);
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(err instanceof HiveApiError ? err.message : "Analytics snapshot unavailable");
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const target = document.getElementById(SECTION_TO_HASH[section]);
    if (target) {
      target.scrollIntoView({ behavior: scrollBehaviorForMotion(), block: "start" });
    }
  }, [section]);

  return (
    <HivePageShell
      title="Analytics Workspace"
      subtitle="Codex-style business analytics — read-only fetch, analyst narrative, critic rubric, export staging."
      status={<ModulePolicyPackPill moduleKey="analytics_workspace" />}
      error={error ? { message: error, onDismiss: () => setError(null) } : null}
      actions={
        snapshot ? (
          <div className="flex flex-wrap items-center gap-2">
            <V4Badge tone={snapshot.swarm_template_built ? "ok" : "warn"}>
              {snapshot.swarm_template_built ? "Swarm built" : "Template ready"}
            </V4Badge>
            <Link
              href="/swarm-builder?template=business-analytics-report"
              className="qs-btn qs-btn--primary qs-btn--sm"
            >
              Open template
            </Link>
          </div>
        ) : null
      }
      subnav={
        <HiveSubnavRow
          items={[
            { id: "overview", label: "Overview", icon: LayoutDashboard },
            { id: "connectors", label: "Connectors", icon: Plug },
            { id: "question", label: "Question", icon: CircleHelp },
            { id: "report", label: "Report", icon: FileText },
            { id: "lineage", label: "Lineage", icon: GitBranch },
            { id: "export", label: "Export inbox", icon: Download },
          ]}
          activeId={section}
          onChange={(id) => {
            const next = id as AnalyticsSection;
            setSection(next);
            updateUrl(next);
          }}
          ariaLabel="Analytics workspace sections"
          menuKey="apps-tools-analytics-workspace"
        />
      }
    >
      {loading ? (
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-5 w-5 animate-spin text-pollen" aria-hidden />
          Loading analytics snapshot…
        </div>
      ) : null}

      {!loading && snapshot && section === "overview" ? (
        <div id="analytics-overview" className="space-y-4" data-testid="analytics-workspace-overview">
          <V4Card>
            <V4CardHeader
              title="Decision report lane"
              description={snapshot.operator_hint}
            />
            <div className="flex flex-wrap gap-2 px-4 pb-4">
              <V4Badge tone="info">{snapshot.capability_key}</V4Badge>
              <V4Badge tone="purple">{snapshot.template_id}</V4Badge>
              {snapshot.skill_slugs.map((slug) => (
                <V4Badge key={slug} tone="gold">
                  {slug}
                </V4Badge>
              ))}
            </div>
          </V4Card>

          <V4Card>
            <V4CardHeader title="Connector slots" description="Read-only default — configure in Integrations." />
            <ul className="space-y-2 px-4 pb-4">
              {snapshot.connector_slots.map((slot) => (
                <li
                  key={slot.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm"
                >
                  <span className="font-medium text-(--qs-text)">{slot.label}</span>
                  <V4Badge tone={slot.ready ? "ok" : "warn"}>{slot.ready ? "ready" : "configure"}</V4Badge>
                  <span className="w-full text-xs text-(--qs-text-3)">{slot.detail}</span>
                </li>
              ))}
            </ul>
            <div className="px-4 pb-4">
              <Link
                href="/apps-tools/analytics?section=connectors#analytics-connectors"
                className="qs-btn qs-btn--ghost qs-btn--sm"
              >
                Open connector profile
              </Link>
            </div>
          </V4Card>

          <V4Card>
            <V4CardHeader title="Operator actions" />
            <div className="grid gap-2 px-4 pb-4">
              {snapshot.actions.map((action) => (
                <Link
                  key={action.id}
                  href={action.href}
                  className="qs-btn qs-btn--ghost qs-btn--sm justify-start text-left"
                >
                  <BarChart3 className="mr-2 h-3.5 w-3.5 shrink-0 text-cyan" aria-hidden />
                  <span>
                    {action.label}
                    <span className="mt-0.5 block text-xs font-normal text-(--qs-text-3)">{action.detail}</span>
                  </span>
                </Link>
              ))}
            </div>
          </V4Card>
        </div>
      ) : null}

      {!loading && snapshot && section === "connectors" ? (
        <div id="analytics-connectors" data-testid="analytics-workspace-connectors">
          <AnalyticsConnectorProfilePanel />
        </div>
      ) : null}

      {!loading && snapshot && section === "question" ? (
        <div id="analytics-question" data-testid="analytics-workspace-question">
          <BusinessQuestionWizardPanel />
        </div>
      ) : null}

      {!loading && snapshot && section === "report" ? (
        <div id="analytics-report" data-testid="analytics-workspace-report">
          <AnalyticsReportArtifactPanel />
        </div>
      ) : null}

      {!loading && snapshot && section === "lineage" ? (
        <div id="analytics-lineage" data-testid="analytics-workspace-lineage">
          <AnalyticsDataLineagePanel />
        </div>
      ) : null}

      {!loading && snapshot && section === "export" ? (
        <V4Card id="analytics-export" data-testid="analytics-workspace-export">
          <V4CardHeader
            title="Export inbox"
            description="Simulate-first Notion/Slides staging after critic rubric ≥4/5."
          />
          <p className="px-4 pb-4 text-sm text-(--qs-text-2)">
            Export lane empty — complete a verified analytics report session first. Live export requires operator
            approval per business-analytics-playbook guardrails.
          </p>
        </V4Card>
      ) : null}
    </HivePageShell>
  );
}
