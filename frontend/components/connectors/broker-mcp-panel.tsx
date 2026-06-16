"use client";

import Link from "next/link";
import { Loader2, Plug, Radio } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

type ProbeStatus = "missing" | "passed" | "failed";

interface RobinhoodMcpStep {
  id: string;
  label: string;
  done: boolean;
  detail: string;
}

interface RobinhoodMcpReadiness {
  enabled: boolean;
  generated_at: string;
  template_id: string;
  connector_slug: string;
  mcp_server_url: string;
  preset_available: boolean;
  connector_installed: boolean;
  oauth_ready: boolean;
  guardrails_ready: boolean;
  guardrails_kill_switch: boolean;
  progress_pct: number;
  ready: boolean;
  last_probe_at: string | null;
  last_probe_status: ProbeStatus;
  last_probe_message: string;
  steps: RobinhoodMcpStep[];
  operator_hint: string;
  install_href: string;
  vault_href: string;
  docs_href: string;
  workspace_href: string;
}

function probeBadge(status: ProbeStatus): { label: string; tone: "ok" | "warn" | "err" } {
  if (status === "passed") return { label: "Probe passed", tone: "ok" };
  if (status === "failed") return { label: "Probe failed", tone: "err" };
  return { label: "Probe pending", tone: "warn" };
}

export function BrokerMcpPanel(): JSX.Element | null {
  const [readiness, setReadiness] = useState<RobinhoodMcpReadiness | null>(null);
  const [loading, setLoading] = useState(true);
  const [probing, setProbing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<RobinhoodMcpReadiness>("trading-cockpit/robinhood-mcp");
      setReadiness(data);
    } catch {
      setReadiness(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runProbe = useCallback(async () => {
    setProbing(true);
    try {
      const result = await hivePostJson<{ ok: boolean; message: string; status: ProbeStatus }>(
        "trading-cockpit/robinhood-mcp/probe",
        {},
      );
      if (result.ok) {
        toast.success(result.message || "Robinhood MCP probe passed.");
      } else {
        toast.error(result.message || "Robinhood MCP probe failed.");
      }
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Probe failed.");
    } finally {
      setProbing(false);
    }
  }, [load]);

  if (loading) {
    return (
      <div data-testid="broker-mcp-panel">
        <V4Card className="flex items-center gap-2 p-4 text-sm text-white/60">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading Broker MCP status…
        </V4Card>
      </div>
    );
  }

  if (!readiness?.enabled) {
    return (
      <div data-testid="broker-mcp-panel">
        <V4Card className="p-4 text-sm text-white/60">Robinhood MCP preset is disabled.</V4Card>
      </div>
    );
  }

  const probe = probeBadge(readiness.last_probe_status);

  return (
    <div className="space-y-4" data-testid="broker-mcp-panel">
      <V4Card id="broker-mcp" className="border-cyan-500/25">
        <V4CardHeader
          leadingIcon={Plug}
          title="Broker MCP — Robinhood Agentic"
          description="MCP server, OAuth, guardrails, and probe before live US equity orders."
          actions={<HiveRefreshButton onClick={() => void load()} aria-label="Refresh broker MCP status" />}
        />
        <p className="mt-3 text-sm text-white/70">{readiness.operator_hint}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <V4Badge tone={readiness.ready ? "ok" : "info"}>{readiness.progress_pct}% ready</V4Badge>
          <V4Badge tone={probe.tone}>{probe.label}</V4Badge>
          {readiness.guardrails_kill_switch ? <V4Badge tone="err">Kill switch ON</V4Badge> : null}
          <Link href={readiness.install_href} className="text-xs text-cyan-300 hover:underline">
            Marketplace install
          </Link>
          <Link href={readiness.vault_href} className="text-xs text-amber-300 hover:underline">
            Connector Vault
          </Link>
        </div>
        <p className="mt-3 font-mono text-[11px] text-white/50">{readiness.mcp_server_url}</p>
      </V4Card>

      <div data-testid="broker-mcp-checklist">
        <V4Card>
          <V4CardHeader leadingIcon={Radio} title="Install checklist" description="RA1 preset + RA2 connect lane" />
          <ul className="mt-4 space-y-3">
            {readiness.steps.map((step) => (
              <li key={step.id} className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <V4Badge tone={step.done ? "ok" : "warn"}>{step.label}</V4Badge>
                </div>
                <p className="mt-2 text-sm text-white/70">{step.detail}</p>
              </li>
            ))}
          </ul>
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" disabled={probing} onClick={() => void runProbe()}>
              {probing ? "Probing…" : "Run connection probe"}
            </button>
            <Link href="/apps-tools/trading-automation?section=guardrails#broker-guardrails" className="qs-btn qs-btn--ghost qs-btn--sm">
              Broker guardrails
            </Link>
            <Link href="/apps-tools/trading-automation?section=orders#broker-order-queue" className="qs-btn qs-btn--ghost qs-btn--sm">
              HITL order queue
            </Link>
          </div>
        </V4Card>
      </div>
    </div>
  );
}
