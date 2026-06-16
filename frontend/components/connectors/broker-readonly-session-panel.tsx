"use client";

import { CheckCircle2, Link2, Loader2, Plug, Radio } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

type SmokeStatus = "missing" | "passed" | "failed";

interface BrokerReadonlyKpi {
  enabled: boolean;
  readonly_required: boolean;
  live_eligible: boolean;
  smoke_status: SmokeStatus;
  smoke_passed_at: string | null;
  smoke_message: string;
  guardrails_ready: boolean;
  guardrails_kill_switch: boolean;
  gamma_connector_ready: boolean;
  clob_connector_ready: boolean;
  last_session_id: string | null;
  last_session_href: string | null;
  template_id: string;
  template_href: string;
  session_bootstrap_href: string;
  operator_hint: string;
  workspace_href: string;
}

function smokeBadge(status: SmokeStatus): { label: string; tone: "ok" | "warn" | "err" } {
  if (status === "passed") return { label: "Smoke passed", tone: "ok" };
  if (status === "failed") return { label: "Smoke failed", tone: "err" };
  return { label: "Smoke pending", tone: "warn" };
}

export function BrokerReadonlySessionPanel(): JSX.Element | null {
  const [kpi, setKpi] = useState<BrokerReadonlyKpi | null>(null);
  const [loading, setLoading] = useState(true);
  const [smoking, setSmoking] = useState(false);
  const [bootstrapping, setBootstrapping] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<BrokerReadonlyKpi>("trading-cockpit/readonly-session");
      setKpi(data);
    } catch {
      setKpi(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runSmoke = useCallback(async () => {
    setSmoking(true);
    try {
      const result = await hivePostJson<{ ok: boolean; message: string; live_eligible: boolean }>(
        "trading-cockpit/readonly-session/smoke",
        {},
      );
      if (result.ok) {
        toast.success(result.message || "Smoke probe passed.");
      } else {
        toast.error(result.message || "Smoke probe failed.");
      }
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Smoke probe failed.");
    } finally {
      setSmoking(false);
    }
  }, [load]);

  const bootstrapSession = useCallback(async () => {
    setBootstrapping(true);
    try {
      const result = await hivePostJson<{ ok: boolean; session_href: string | null; message: string }>(
        "trading-cockpit/readonly-session/bootstrap",
        {},
      );
      if (result.ok && result.session_href) {
        toast.success(result.message || "Read-only session started.");
        await load();
        window.location.href = result.session_href;
        return;
      }
      toast.error(result.message || "Bootstrap failed.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Bootstrap failed.");
    } finally {
      setBootstrapping(false);
    }
  }, [load]);

  if (loading) {
    return (
      <div data-testid="broker-readonly-session-panel">
        <V4Card className="flex items-center gap-2 p-4 text-sm text-white/60">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading read-only broker session…
        </V4Card>
      </div>
    );
  }

  if (!kpi?.enabled) {
    return null;
  }

  const smoke = smokeBadge(kpi.smoke_status);

  return (
    <div id="broker-readonly-session" data-testid="broker-readonly-session-panel">
      <V4Card className="space-y-4 p-4">
        <V4CardHeader
          kicker="Track P · RA4"
          title="Read-only broker session"
          description="Portfolio & quotes only until smoke + guardrails configured."
          leadingIcon={Plug}
          actions={<HiveRefreshButton busy={loading} onClick={() => void load()} />}
        />

        <p className="text-sm text-white/70">{kpi.operator_hint}</p>

        <div className="flex flex-wrap gap-2">
          <V4Badge tone={smoke.tone}>{smoke.label}</V4Badge>
          <V4Badge tone={kpi.live_eligible ? "ok" : "warn"}>
            {kpi.live_eligible ? "Live eligible" : "Read-only required"}
          </V4Badge>
          <V4Badge tone={kpi.gamma_connector_ready ? "ok" : "err"}>
            Gamma {kpi.gamma_connector_ready ? "ready" : "missing"}
          </V4Badge>
          <V4Badge tone={kpi.guardrails_ready ? "ok" : "warn"}>
            Guardrails {kpi.guardrails_ready ? "saved" : "pending"}
          </V4Badge>
        </div>

        {kpi.smoke_message ? <p className="font-mono text-xs text-white/50">{kpi.smoke_message}</p> : null}

        <ul className="space-y-1 text-sm text-white/60">
          <li className="flex items-center gap-2">
            <CheckCircle2 className={`size-4 ${kpi.gamma_connector_ready ? "text-[#00FF88]" : "text-white/30"}`} />
            Install polymarket_gamma connector
          </li>
          <li className="flex items-center gap-2">
            <CheckCircle2 className={`size-4 ${kpi.guardrails_ready ? "text-[#00FF88]" : "text-white/30"}`} />
            Save broker guardrails (tenant overrides)
          </li>
          <li className="flex items-center gap-2">
            <CheckCircle2 className={`size-4 ${kpi.smoke_status === "passed" ? "text-[#00FF88]" : "text-white/30"}`} />
            Run read-only smoke probe
          </li>
        </ul>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm"
            disabled={smoking}
            onClick={() => void runSmoke()}
          >
            {smoking ? <Loader2 className="size-4 animate-spin" /> : <Radio className="size-4" />}
            Run smoke probe
          </button>
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm"
            disabled={bootstrapping}
            onClick={() => void bootstrapSession()}
          >
            {bootstrapping ? <Loader2 className="size-4 animate-spin" /> : <Link2 className="size-4" />}
            Start read-only session
          </button>
          <Link href={kpi.template_href} className="qs-btn qs-btn--ghost qs-btn--sm">
            Open swarm template
          </Link>
          <Link
            href="/apps-tools/trading-automation?section=guardrails#broker-guardrails"
            className="qs-btn qs-btn--ghost qs-btn--sm"
          >
            Broker guardrails
          </Link>
        </div>

        {kpi.last_session_href ? (
          <p className="text-xs text-white/50">
            Last session:{" "}
            <Link href={kpi.last_session_href} className="text-[#00FFFF] hover:underline">
              {kpi.last_session_id}
            </Link>
          </p>
        ) : null}
      </V4Card>
    </div>
  );
}
