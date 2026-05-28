"use client";

import { Loader2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { CollapsibleLazyPanel } from "@/components/hive/collapsible-lazy-panel";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { usePlatform } from "@/components/hive/platform-context";
import { hiveGet, hivePostJson, HiveApiError } from "@/lib/api";
import type { HarnessIntelligenceScanPayload, HarnessSnapshotPayload } from "@/lib/hive-types";
import { BehavioralMemoryPanel } from "@/components/hive/behavioral-memory-panel";
import {
  HarnessMcpToolGrid,
  HarnessPatternGrid,
  HarnessSkillLatticeGrid,
} from "@/components/hive/harness-snapshot-grids";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { SoloOperatorTrioPanel } from "@/components/hive/solo-operator-trio-panel";
import { SlackHarnessTrainerPanel } from "@/components/hive/slack-harness-trainer-panel";
import { LspBridgePanel } from "@/components/hive/lsp-bridge-panel";
import { RubricTemplatesPanel } from "@/components/hive/rubric-templates-panel";
import { QueenMaintainerWebhookPanel } from "@/components/hive/queen-maintainer-webhook-panel";
import type { HarnessRulesSection } from "@/lib/settings-harness-rules-routes";
import { HARNESS_LOOPS_PANEL_SPECS } from "@/lib/settings-panel-density";
import { cn } from "@/lib/utils";

interface SettingsHarnessPanelProps {
  section: HarnessRulesSection;
}

export function SettingsHarnessPanel({ section }: SettingsHarnessPanelProps): JSX.Element | null {
  const { hasFeature } = usePlatform();
  const [loading, setLoading] = useState(true);
  const [scanBusy, setScanBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<HarnessSnapshotPayload | null>(null);
  const [scan, setScan] = useState<HarnessIntelligenceScanPayload | null>(null);

  const load = useCallback(async () => {
    if (!hasFeature("ai_harness_dashboard")) {
      setLoading(false);
      return;
    }
    try {
      const body = await hiveGet<HarnessSnapshotPayload>("harness/snapshot");
      setSnapshot(body);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Harness snapshot unavailable.");
    } finally {
      setLoading(false);
    }
  }, [hasFeature]);

  useEffect(() => {
    void load();
  }, [load]);

  async function runScan(): Promise<void> {
    setScanBusy(true);
    try {
      const body = await hivePostJson<HarnessIntelligenceScanPayload>("harness/intelligence-scan", {});
      setScan(body);
      toast.success(`Intelligence scan: ${body.proposal_count} proposal(s)`);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Scan failed.");
    } finally {
      setScanBusy(false);
    }
  }

  if (!hasFeature("ai_harness_dashboard")) {
    return null;
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-(--qs-muted)">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Loading AI Layer harness…
      </div>
    );
  }

  if (err || !snapshot) {
    return (
      <V4Card>
        <p className="text-sm text-[#FF3366]">{err ?? "No harness data."}</p>
      </V4Card>
    );
  }

  if (section === "overview") {
    return (
      <V4Card id="rules-overview" className="scroll-mt-28">
        <V4CardHeader
          kicker="AI Layer"
          title="Harness visibility"
          description="Layered rules, active skills, MCP tools, and recent agentic design patterns — harness &gt; model."
          hint={sectionHintNode("harnessRulesOverview")}
        />
        <div className="mt-4 flex flex-wrap gap-2">
          <V4Badge tone="info">Skills {snapshot.skills.count}</V4Badge>
          <V4Badge tone="info">MCP {snapshot.mcp_tools.count}</V4Badge>
          <V4Badge tone={(snapshot.tech_health_score ?? 0) >= 0.7 ? "ok" : "warn"}>
            Tech health {((snapshot.tech_health_score ?? 0) * 100).toFixed(0)}%
          </V4Badge>
          {snapshot.feature_flags.supervisor_pattern_router_enabled ? (
            <V4Badge tone="ok">Pattern Router</V4Badge>
          ) : null}
          {snapshot.feature_flags.supervisor_pattern_router_llm_enabled ? (
            <V4Badge tone="info">LLM refine</V4Badge>
          ) : (
            <V4Badge tone="info">LLM refine off</V4Badge>
          )}
          {snapshot.feature_flags.skill_lazy_reference_fetch_enabled ? (
            <V4Badge tone="ok">Skill refs lazy</V4Badge>
          ) : null}
          {snapshot.skills.reference_mode_count != null && snapshot.skills.reference_mode_count > 0 ? (
            <V4Badge tone="info">Ref skills {snapshot.skills.reference_mode_count}</V4Badge>
          ) : null}
          {snapshot.feature_flags.supervisor_forced_reflection_enabled ? (
            <V4Badge tone="ok">Forced reflection</V4Badge>
          ) : null}
        </div>
      </V4Card>
    );
  }

  if (section === "monitoring") {
    return (
      <V4Card id="rules-monitoring" className="scroll-mt-28">
        <V4CardHeader
          kicker="Observability"
          title="Pattern monitoring"
          description="Prometheus alert rules, Alertmanager routing, and 24h pattern success telemetry."
          hint={sectionHintNode("harnessRulesMonitoring")}
        />
        <div className="mt-3 flex flex-wrap gap-2">
          <V4Badge tone={snapshot.monitoring.slack_webhook_configured ? "ok" : "warn"}>
            Slack {snapshot.monitoring.slack_webhook_configured ? "on" : "off"}
          </V4Badge>
          <V4Badge tone="info">{snapshot.monitoring.alertmanager_receiver}</V4Badge>
          <V4Badge tone="info">{snapshot.monitoring.pattern_alert_rules.length} alert rules</V4Badge>
        </div>
        <ul className="mt-3 space-y-1 text-sm text-(--qs-muted)">
          {snapshot.monitoring.pattern_alert_rules.map((rule) => (
            <li key={rule} className="font-mono text-xs text-cyan">
              {rule}
            </li>
          ))}
        </ul>
        {snapshot.monitoring.pattern_telemetry ? (
          <div className="mt-4 space-y-2">
            <p className="text-xs text-(--qs-muted)">
              {snapshot.monitoring.pattern_telemetry.sessions_analyzed} sessions ·{" "}
              {snapshot.monitoring.pattern_telemetry.patterns_tracked} patterns (24h)
            </p>
            <ul className="grid gap-2 md:grid-cols-2">
              {snapshot.monitoring.pattern_telemetry.top_patterns.map((row) => (
                <li
                  key={row.id}
                  className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2 text-sm"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-(--qs-text)">{row.label}</span>
                    <V4Badge
                      tone={
                        (row.success_rate_pct ?? 0) >= 80
                          ? "ok"
                          : (row.success_rate_pct ?? 0) >= 50
                            ? "warn"
                            : "err"
                      }
                    >
                      {row.success_rate_pct != null ? `${row.success_rate_pct}%` : "—"}
                    </V4Badge>
                  </div>
                  <p className="mt-1 font-mono text-xs text-(--qs-muted)">
                    {row.success_count} ok · {row.failure_count} fail · {row.sessions} sessions
                  </p>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="mt-3 text-sm text-(--qs-muted)">No verified pattern sessions in the last 24h yet.</p>
        )}
        <p className="mt-3 font-mono text-xs text-(--qs-muted)">
          Grafana: {snapshot.monitoring.grafana_dashboard_uid} · smoke: {snapshot.monitoring.smoke_script}
        </p>
      </V4Card>
    );
  }

  if (section === "files") {
    return (
      <V4Card id="rules-files" className="scroll-mt-28">
        <V4CardHeader
          kicker="Rules"
          title="Layered harness files"
          description="Root .cursorrules + scoped .cursor/rules — lean global context."
          hint={sectionHintNode("harnessRulesFiles")}
        />
        <ul className="mt-3 space-y-2">
          {snapshot.rule_layers.map((layer) => (
            <li
              key={layer.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2 text-sm"
            >
              <span className="font-mono text-cyan">{layer.path}</span>
              <span className="text-(--qs-muted)">
                {layer.scope} · {layer.bytes} B
              </span>
            </li>
          ))}
        </ul>
      </V4Card>
    );
  }

  if (section === "tools") {
    return (
      <V4Card id="rules-tools" className="scroll-mt-28">
        <V4CardHeader
          kicker="MCP"
          title="Dynamic tool catalog"
          description="Active connector tools discoverable by supervisor lanes."
          hint={sectionHintNode("harnessRulesTools")}
        />
        <div className="mt-4">
          <HarnessMcpToolGrid items={snapshot.mcp_tools.items} />
        </div>
      </V4Card>
    );
  }

  if (section === "skills") {
    return (
      <div id="rules-skills" className="scroll-mt-28 space-y-6">
        <V4Card>
          <V4CardHeader
            kicker="Skills"
            title="Active skill lattice"
            description="Markdown skills selected by SkillLibrary."
            hint={sectionHintNode("harnessRulesSkills")}
          />
          <div className="mt-4">
            <HarnessSkillLatticeGrid skills={snapshot.skills.items} />
          </div>
        </V4Card>
        <BehavioralMemoryPanel />
      </div>
    );
  }

  return (
    <div id="rules-loops" className="settings-panel-density scroll-mt-28 space-y-4" data-testid="settings-harness-loops">
      <V4Card>
        <V4CardHeader
          kicker="Operator"
          title="Operator loops"
          description="Solo trio, Slack trainer, LSP bridge, rubrics, maintainer webhook, recent patterns, and Forager scan."
          hint={sectionHintNode("harnessRulesLoops")}
        />
      </V4Card>

      {HARNESS_LOOPS_PANEL_SPECS.filter((spec) => {
        if (spec.id === "harness-loops-slack") {
          return hasFeature("slack_harness_trainer");
        }
        if (spec.id === "harness-loops-lsp") {
          return hasFeature("lsp_mcp_bridge");
        }
        if (spec.id === "harness-loops-rubric") {
          return hasFeature("rubric_templates");
        }
        return true;
      }).map((spec) => (
        <CollapsibleLazyPanel
          key={spec.id}
          id={spec.id}
          hashKey={spec.hashKey}
          title={spec.title}
          hint={spec.hint}
          defaultOpen={spec.defaultOpen ?? false}
          lazyContent={() => {
            if (spec.id === "harness-loops-trio") {
              return <SoloOperatorTrioPanel />;
            }
            if (spec.id === "harness-loops-slack" && hasFeature("slack_harness_trainer")) {
              return <SlackHarnessTrainerPanel snapshot={snapshot} />;
            }
            if (spec.id === "harness-loops-lsp" && hasFeature("lsp_mcp_bridge")) {
              return <LspBridgePanel snapshot={snapshot} />;
            }
            if (spec.id === "harness-loops-rubric" && hasFeature("rubric_templates")) {
              return <RubricTemplatesPanel snapshot={snapshot} />;
            }
            if (spec.id === "harness-loops-maintainer") {
              return <QueenMaintainerWebhookPanel snapshot={snapshot} />;
            }
            if (spec.id === "harness-loops-patterns") {
              return (
                <V4Card className="border-0 bg-transparent p-0 shadow-none">
                  <V4CardHeader
                    kicker="Patterns"
                    title="Recent agentic patterns"
                    description="From supervisor sessions — Pattern Router selections."
                  />
                  <div className="mt-4">
                    <HarnessPatternGrid patterns={snapshot.recent_agentic_patterns} />
                  </div>
                </V4Card>
              );
            }
            if (spec.id === "harness-loops-forager") {
              return (
                <V4Card className="border-0 bg-transparent p-0 shadow-none">
                  <V4CardHeader
                    kicker="Forager"
                    title="Intelligence Loop"
                    description="Read-only scan — skill/MCP/doc refresh proposals (Langfuse-style freshness)."
                  />
                  {snapshot.forager_intelligence ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      <V4Badge tone={snapshot.forager_intelligence.enabled ? "ok" : "info"}>
                        Daily beat {snapshot.forager_intelligence.enabled ? "on" : "off"}
                      </V4Badge>
                      <V4Badge tone="info">UTC {snapshot.forager_intelligence.cron_utc}</V4Badge>
                      <V4Badge tone="info">{snapshot.forager_intelligence.celery_task}</V4Badge>
                    </div>
                  ) : null}
                  <button
                    type="button"
                    className={cn("qs-btn qs-btn--ghost qs-btn--sm mt-3", scanBusy && "opacity-60")}
                    disabled={scanBusy}
                    onClick={() => void runScan()}
                  >
                    {scanBusy ? (
                      <Loader2 className="size-4 animate-spin" aria-hidden />
                    ) : (
                      <RefreshCw className="size-4" aria-hidden />
                    )}
                    Run intelligence scan
                  </button>
                  {scan && scan.proposals.length > 0 ? (
                    <ul className="mt-4 space-y-2">
                      {scan.proposals.slice(0, 8).map((item, idx) => (
                        <li
                          key={`${item.kind}-${item.target}-${idx}`}
                          className="rounded-lg border border-(--qs-border) bg-black/20 p-3 text-sm"
                        >
                          <div className="flex flex-wrap gap-2">
                            <V4Badge tone={item.priority === "high" ? "warn" : "info"}>{item.kind}</V4Badge>
                            <span className="font-mono text-cyan">{item.target}</span>
                          </div>
                          <p className="mt-2 text-(--qs-muted)">{item.rationale}</p>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </V4Card>
              );
            }
            return null;
          }}
        />
      ))}
    </div>
  );
}
