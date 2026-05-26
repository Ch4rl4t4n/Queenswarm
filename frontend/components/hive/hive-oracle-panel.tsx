"use client";

import Link from "next/link";
import { Loader2, RefreshCw, Sparkles } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { cn } from "@/lib/utils";

interface OracleWarning {
  id: string;
  severity: "low" | "medium" | "high" | "critical";
  message: string;
  fix_href?: string | null;
  confidence_pct: number;
}

interface OraclePrediction {
  id: string;
  horizon: "today" | "week";
  message: string;
  likelihood_pct: number;
}

interface HiveOracleSnapshot {
  enabled: boolean;
  warnings: OracleWarning[];
  predictions: OraclePrediction[];
  synthesis_md: string;
  synthesis_model: string | null;
  llm_synthesis_enabled: boolean;
  metrics: Record<string, number>;
}

function severityTone(s: OracleWarning["severity"]): "ok" | "warn" | "err" | "info" {
  if (s === "critical" || s === "high") return "err";
  if (s === "medium") return "warn";
  return "info";
}

function HiveOraclePanelInner() {
  const [snapshot, setSnapshot] = useState<HiveOracleSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [synthesisLoading, setSynthesisLoading] = useState(false);

  const load = useCallback(async (withSynthesis = false) => {
    if (withSynthesis) setSynthesisLoading(true);
    else setLoading(true);
    try {
      const path = withSynthesis ? "operator/oracle?synthesis=true" : "operator/oracle";
      const data = await hiveGet<HiveOracleSnapshot>(path);
      setSnapshot(data);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Oracle unavailable");
    } finally {
      setLoading(false);
      setSynthesisLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(false);
  }, [load]);

  if (loading && !snapshot) {
    return (
      <p className="flex items-center gap-2 text-sm text-(--qs-muted)">
        <Loader2 className="size-4 animate-spin" aria-hidden /> Loading Hive Oracle…
      </p>
    );
  }

  if (!snapshot?.enabled) {
    return (
      <V4Card>
        <p className="text-sm text-(--qs-muted)">Hive Oracle is disabled on this deployment.</p>
      </V4Card>
    );
  }

  return (
    <div className="space-y-6">
      <V4Card>
        <V4CardHeader
          kicker="Hive Oracle v2"
          title="Predictive warnings"
          description="Heuristické signály z fleet, publish lane a trio — verify-first."
        />
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <V4Badge tone="info">Warnings {snapshot.warnings.length}</V4Badge>
          <V4Badge tone="info">Predictions {snapshot.predictions.length}</V4Badge>
          <V4Badge tone={snapshot.llm_synthesis_enabled ? "ok" : "warn"}>
            LLM synthesis {snapshot.llm_synthesis_enabled ? "on" : "off"}
          </V4Badge>
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void load(false)}>
            <RefreshCw className={cn("size-4", loading && "animate-spin")} aria-hidden />
            Refresh
          </button>
          <Link href="/cockpit" className="qs-btn qs-btn--ghost qs-btn--sm">
            Cockpit
          </Link>
        </div>

        {snapshot.warnings.length === 0 ? (
          <p className="text-sm text-(--qs-muted)">No active warnings — hive signals look stable.</p>
        ) : (
          <ul className="space-y-2">
            {snapshot.warnings.map((w) => (
              <li
                key={w.id}
                className="flex flex-wrap items-start justify-between gap-2 rounded-lg border border-pollen/30 bg-pollen/5 px-3 py-2"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <V4Badge tone={severityTone(w.severity)}>{w.severity}</V4Badge>
                    <span className="text-xs text-(--qs-muted)">{w.confidence_pct}% confidence</span>
                  </div>
                  <p className="mt-1 text-sm text-(--qs-text)">{w.message}</p>
                </div>
                {w.fix_href ? (
                  <Link href={w.fix_href} className="qs-btn qs-btn--ghost qs-btn--sm shrink-0">
                    Fix
                  </Link>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </V4Card>

      <V4Card>
        <V4CardHeader kicker="Forward view" title="Predictions" description="Krátky horizont — today / week." />
        {snapshot.predictions.length === 0 ? (
          <p className="text-xs text-(--qs-muted)">No predictions yet.</p>
        ) : (
          <ul className="space-y-2">
            {snapshot.predictions.map((p) => (
              <li key={p.id} className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <V4Badge tone="info">{p.horizon}</V4Badge>
                  <span className="text-xs text-(--qs-muted)">~{p.likelihood_pct}%</span>
                </div>
                <p className="mt-1 text-(--qs-text)">{p.message}</p>
              </li>
            ))}
          </ul>
        )}
      </V4Card>

      <V4Card>
        <V4CardHeader
          kicker="LLM-light"
          title="Oracle synthesis"
          description="Voliteľný cheap model brief — zapni HIVE_ORACLE_LLM_SYNTHESIS_ENABLED."
        />
        {snapshot.synthesis_md ? (
          <p className="whitespace-pre-wrap text-sm text-(--qs-text)">{snapshot.synthesis_md}</p>
        ) : (
          <p className="text-xs text-(--qs-muted)">
            {snapshot.llm_synthesis_enabled
              ? "Klikni Synthesize pre LLM brief."
              : "LLM synthesis vypnutá — len heuristiky."}
          </p>
        )}
        {snapshot.llm_synthesis_enabled ? (
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm mt-3 gap-1"
            disabled={synthesisLoading}
            onClick={() => void load(true)}
          >
            {synthesisLoading ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Sparkles className="size-4" />
            )}
            Synthesize
          </button>
        ) : null}
        {snapshot.synthesis_model ? (
          <p className="mt-2 font-mono text-[10px] text-(--qs-muted)">Model: {snapshot.synthesis_model}</p>
        ) : null}
      </V4Card>
    </div>
  );
}

export const HiveOraclePanel = memo(HiveOraclePanelInner);

export const LazyHiveOraclePanel = memo(function LazyHiveOraclePanel() {
  return <HiveOraclePanel />;
});
