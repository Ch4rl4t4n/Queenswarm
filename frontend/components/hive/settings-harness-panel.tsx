"use client";

import { Loader2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { usePlatform } from "@/components/hive/platform-context";
import { hiveGet, hivePostJson, HiveApiError } from "@/lib/api";
import type { HarnessIntelligenceScanPayload, HarnessSnapshotPayload } from "@/lib/hive-types";
import { BehavioralMemoryPanel } from "@/components/hive/behavioral-memory-panel";
import { CollapsibleLazyPanel } from "@/components/hive/collapsible-lazy-panel";
import {
  HarnessMcpToolGrid,
  HarnessPatternGrid,
  HarnessSkillLatticeGrid,
} from "@/components/hive/harness-snapshot-grids";
import { SoloOperatorTrioPanel } from "@/components/hive/solo-operator-trio-panel";
import { SlackHarnessTrainerPanel } from "@/components/hive/slack-harness-trainer-panel";
import { LspBridgePanel } from "@/components/hive/lsp-bridge-panel";
import { RubricTemplatesPanel } from "@/components/hive/rubric-templates-panel";
import { QueenMaintainerWebhookPanel } from "@/components/hive/queen-maintainer-webhook-panel";
import { cn } from "@/lib/utils";

export function SettingsHarnessPanel(): JSX.Element | null {
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

  return (
    <div className="space-y-6">
      <V4Card>
        <V4CardHeader
          kicker="AI Layer"
          title="Harness visibility"
          description="Layered rules, active skills, MCP tools, and recent agentic design patterns — harness &gt; model."
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

      <V4Card>
        <V4CardHeader
          kicker="Observability"
          title="Pattern monitoring"
          description="Prometheus alert rules, Alertmanager routing, and 24h pattern success telemetry."
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
                    <V4Badge tone={(row.success_rate_pct ?? 0) >= 80 ? "ok" : (row.success_rate_pct ?? 0) >= 50 ? "warn" : "err"}>
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

      <V4Card>
        <V4CardHeader
          kicker="Rules"
          title="Layered harness files"
          description="Root .cursorrules + scoped .cursor/rules — lean global context."
        />
        <ul className="mt-3 space-y-2">
          {snapshot.rule_layers.map((layer) => (
            <li
              key={layer.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2 text-sm"
            >
              <span className="font-mono text-cyan">{layer.path}</span>
              <span className="text-(--qs-muted)">{layer.scope} · {layer.bytes} B</span>
            </li>
          ))}
        </ul>
      </V4Card>

      <CollapsibleLazyPanel
        id="harness-tool-catalog"
        hashKey="tool-catalog"
        title="Dynamic tool catalog"
        hint="Active connector tools discoverable by supervisor lanes."
        meta={`${snapshot.mcp_tools.count} tools`}
        lazyContent={() => <HarnessMcpToolGrid items={snapshot.mcp_tools.items} />}
      />

      <SoloOperatorTrioPanel />
      <BehavioralMemoryPanel />
      {hasFeature("slack_harness_trainer") && snapshot ? (
        <SlackHarnessTrainerPanel snapshot={snapshot} />
      ) : null}
      {hasFeature("lsp_mcp_bridge") && snapshot ? <LspBridgePanel snapshot={snapshot} /> : null}
      {hasFeature("rubric_templates") && snapshot ? <RubricTemplatesPanel snapshot={snapshot} /> : null}
      {snapshot ? <QueenMaintainerWebhookPanel snapshot={snapshot} /> : null}

      <CollapsibleLazyPanel
        id="harness-skill-lattice"
        hashKey="skill-lattice"
        title="Active skill lattice"
        hint="Markdown skills selected by SkillLibrary."
        meta={`${snapshot.skills.count} skills`}
        lazyContent={() => <HarnessSkillLatticeGrid skills={snapshot.skills.items} />}
      />

      <CollapsibleLazyPanel
        id="harness-recent-patterns"
        hashKey="recent-patterns"
        title="Recent agentic patterns"
        hint="From supervisor sessions — Pattern Router selections."
        meta={`${snapshot.recent_agentic_patterns.length} sessions`}
        lazyContent={() => <HarnessPatternGrid patterns={snapshot.recent_agentic_patterns} />}
      />

      <V4Card>
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
          {scanBusy ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <RefreshCw className="size-4" aria-hidden />}
          Run intelligence scan
        </button>
        {scan && scan.proposals.length > 0 ? (
          <ul className="mt-4 space-y-2">
            {scan.proposals.slice(0, 8).map((item, idx) => (
              <li key={`${item.kind}-${item.target}-${idx}`} className="rounded-lg border border-(--qs-border) bg-black/20 p-3 text-sm">
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
    </div>
  );
}
