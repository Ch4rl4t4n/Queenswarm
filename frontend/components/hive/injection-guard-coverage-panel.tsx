"use client";

import { Loader2, ShieldAlert } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { hiveGet } from "@/lib/api";
import { cn } from "@/lib/utils";

type CoverageStatus = "healthy" | "warn" | "critical";

interface InjectionGuardCheckpointState {
  checkpoint_id: string;
  label: string;
  scans: number;
  blocked: number;
  block_rate_pct: number;
  coverage_pct: number;
}

interface InjectionGuardToolState {
  tool_name: string;
  label: string;
  scans: number;
  blocked: number;
  covered: boolean;
  checkpoint_id: string;
}

interface InjectionGuardHitState {
  at: string;
  checkpoint_id: string;
  checkpoint_label: string;
  tool_name: string | null;
  matched_pattern: string | null;
}

interface InjectionGuardCoverageState {
  enabled: boolean;
  status: CoverageStatus;
  total_scans: number;
  total_blocked: number;
  guarded_tool_count: number;
  checkpoints: InjectionGuardCheckpointState[];
  tools: InjectionGuardToolState[];
  recent_hits: InjectionGuardHitState[];
  operator_hint: string;
  updated_at: string | null;
}

function statusTone(status: CoverageStatus): string {
  if (status === "critical") {
    return "border-(--qs-red)/40 bg-(--qs-red)/10";
  }
  if (status === "warn") {
    return "border-pollen/40 bg-pollen/10";
  }
  return "border-success/35 bg-success/5";
}

/** TR1 — Injection guard coverage dashboard (3-checkpoint model). */
export function InjectionGuardCoveragePanel(): JSX.Element | null {
  const [state, setState] = useState<InjectionGuardCoverageState | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<InjectionGuardCoverageState>("harness/injection-guard-coverage");
      setState(data);
    } catch {
      setState(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading && !state) {
    return (
      <div className="flex min-h-24 items-center gap-2 text-sm text-(--qs-text-3)">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Loading injection guard coverage…
      </div>
    );
  }

  if (!state?.enabled) {
    return null;
  }

  return (
    <V4Card className={cn("border-(--qs-border)", statusTone(state.status))} data-testid="injection-guard-coverage-panel">
      <V4CardHeader
        leadingIcon={ShieldAlert}
        leadingIconTone="cyan"
        title="Injection guard coverage"
        description="OW15–17 · 3-checkpoint model — operator input, external tools, agent output."
        hint={sectionHintNode("harnessInjectionGuard")}
        actions={
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void load()}>
            Refresh
          </button>
        }
      />

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <V4Badge tone="gold">TR1</V4Badge>
        <V4Badge tone={state.status === "healthy" ? "ok" : state.status === "warn" ? "warn" : "err"}>
          {state.status}
        </V4Badge>
        <V4Badge tone="info">{state.guarded_tool_count} guarded tools</V4Badge>
        <span className="font-mono text-xs text-(--qs-text-3)">
          {state.total_blocked}/{state.total_scans} blocked scans
        </span>
      </div>

      <p className="mb-3 text-xs text-(--qs-text-3)">{state.operator_hint}</p>

      <div className="grid gap-2 sm:grid-cols-3">
        {state.checkpoints.map((checkpoint) => (
          <div
            key={checkpoint.checkpoint_id}
            className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2"
            data-testid={`injection-checkpoint-${checkpoint.checkpoint_id}`}
          >
            <p className="text-xs font-semibold text-(--qs-text-2)">{checkpoint.label}</p>
            <p className="mt-1 font-mono text-[11px] text-cyan">
              {checkpoint.blocked}/{checkpoint.scans} blocked · {checkpoint.block_rate_pct}%
            </p>
            <p className="text-[10px] text-(--qs-text-4)">coverage {checkpoint.coverage_pct}%</p>
          </div>
        ))}
      </div>

      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[480px] text-left text-xs">
          <thead>
            <tr className="text-[10px] uppercase tracking-wide text-(--qs-text-4)">
              <th className="pb-2 pr-3">Tool</th>
              <th className="pb-2 pr-3">Scans</th>
              <th className="pb-2 pr-3">Blocked</th>
              <th className="pb-2">Covered</th>
            </tr>
          </thead>
          <tbody>
            {state.tools.map((tool) => (
              <tr key={tool.tool_name} className="border-t border-(--qs-border)/60">
                <td className="py-2 pr-3 font-medium text-(--qs-text-2)">{tool.label}</td>
                <td className="py-2 pr-3 font-mono text-(--qs-text-3)">{tool.scans}</td>
                <td className="py-2 pr-3 font-mono text-(--qs-text-3)">{tool.blocked}</td>
                <td className="py-2">
                  <V4Badge tone={tool.covered ? "ok" : "err"}>{tool.covered ? "yes" : "no"}</V4Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {state.recent_hits.length > 0 ? (
        <div className="mt-3 space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-(--qs-text-4)">Recent blocks</p>
          <ul className="space-y-1.5">
            {state.recent_hits.map((hit) => (
              <li
                key={`${hit.at}-${hit.checkpoint_id}-${hit.tool_name ?? "none"}`}
                className="rounded-md border border-(--qs-red)/25 bg-(--qs-red)/5 px-2.5 py-2 text-[11px] text-(--qs-text-2)"
              >
                <span className="font-semibold text-(--qs-red)">{hit.checkpoint_label}</span>
                {hit.tool_name ? <span className="ml-2 font-mono text-cyan">{hit.tool_name}</span> : null}
                {hit.matched_pattern ? (
                  <span className="mt-1 block font-mono text-[10px] text-(--qs-text-4)">{hit.matched_pattern}</span>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </V4Card>
  );
}
