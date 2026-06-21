/** TR4 — Skill Factory queue SLO panel. */

"use client";

import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";
import Link from "next/link";

import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { cn } from "@/lib/utils";

export interface FactoryQueueSlo {
  enabled: boolean;
  status: "healthy" | "warn" | "critical";
  awaiting_forge: number;
  awaiting_forge_warn: number;
  awaiting_forge_critical: number;
  critic_approval_rate: number | null;
  critic_samples: number;
  weekly_builds_used: number;
  weekly_build_cap: number;
  weekly_cap_pct: number;
  alerts: string[];
  next_operator_action: string;
  loop5_preset_id?: string | null;
  loop5_preset_label?: string | null;
  loop5_min_score?: number | null;
  loop5_max_turns?: number | null;
}

interface FactoryQueueSloPanelProps {
  slo: FactoryQueueSlo | null | undefined;
}

function statusTone(status: FactoryQueueSlo["status"]): string {
  if (status === "critical") {
    return "border-[#FF3366]/50 bg-[#FF3366]/5";
  }
  if (status === "warn") {
    return "border-[#FFB800]/40 bg-[#FFB800]/5";
  }
  return "border-[#00FF88]/30 bg-[#00FF88]/5";
}

function statusBadge(status: FactoryQueueSlo["status"]): JSX.Element {
  if (status === "critical") {
    return <V4Badge tone="err">Critical</V4Badge>;
  }
  if (status === "warn") {
    return <V4Badge tone="warn">Warn</V4Badge>;
  }
  return <V4Badge tone="ok">Healthy</V4Badge>;
}

export function FactoryQueueSloPanel({ slo }: FactoryQueueSloPanelProps): JSX.Element | null {
  if (!slo?.enabled) {
    return null;
  }

  const criticPct =
    slo.critic_approval_rate != null ? `${Math.round(slo.critic_approval_rate * 100)}%` : "—";
  const weeklyPct = `${Math.round(slo.weekly_cap_pct * 100)}%`;

  return (
    <V4Card
      id="factory-queue-slo"
      className={cn("mb-4 shrink-0", statusTone(slo.status))}
    >
      <V4CardHeader
        title="Queue SLO"
        description="TR4 — awaiting forge · critic rate · weekly cap"
        hint={sectionHintNode("skillFactoryQueueSlo")}
        actions={statusBadge(slo.status)}
      />
      <div className="grid gap-3 px-4 pb-4 sm:grid-cols-3">
        <div className="rounded-md border border-white/10 bg-black/20 p-3">
          <p className="text-xs text-white/60">Awaiting forge</p>
          <p className="font-mono text-lg text-[#00FFFF]">
            {slo.awaiting_forge}
            <span className="text-xs text-white/50">
              {" "}
              / warn {slo.awaiting_forge_warn} · crit {slo.awaiting_forge_critical}
            </span>
          </p>
        </div>
        <div className="rounded-md border border-white/10 bg-black/20 p-3">
          <p className="text-xs text-white/60">Critic approval</p>
          <p className="font-mono text-lg text-[#FFB800]">
            {criticPct}
            <span className="text-xs text-white/50"> ({slo.critic_samples} samples)</span>
          </p>
        </div>
        <div className="rounded-md border border-white/10 bg-black/20 p-3">
          <p className="text-xs text-white/60">Weekly builds</p>
          <p className="font-mono text-lg text-[#00FF88]">
            {slo.weekly_builds_used}/{slo.weekly_build_cap}
            <span className="text-xs text-white/50"> ({weeklyPct})</span>
          </p>
        </div>
      </div>
      {slo.alerts.length > 0 ? (
        <ul className="space-y-1 px-4 pb-3 text-sm text-[#FFB800]">
          {slo.alerts.map((alert) => (
            <li key={alert} className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
              {alert}
            </li>
          ))}
        </ul>
      ) : (
        <p className="flex items-center gap-2 px-4 pb-3 text-sm text-[#00FF88]">
          <CheckCircle2 className="size-4 shrink-0" aria-hidden />
          All queue SLO checks passing.
        </p>
      )}
      <p className="border-t border-white/10 px-4 py-3 text-sm text-white/80">
        <span className="text-white/50">Next: </span>
        {slo.next_operator_action}
        {slo.loop5_preset_label ? (
          <span className="mt-1 block text-xs text-white/50">
            LOOP5 preset: {slo.loop5_preset_label}
            {slo.loop5_min_score != null && slo.loop5_max_turns != null
              ? ` · min ${(slo.loop5_min_score * 5).toFixed(1)}/5 · ${slo.loop5_max_turns} turns`
              : null}
          </span>
        ) : null}
        {slo.status !== "healthy" ? (
          <>
            {" "}
            <Link href="#factory-queue" className="text-[#00FFFF] underline-offset-2 hover:underline">
              Open queue
            </Link>
          </>
        ) : null}
      </p>
    </V4Card>
  );
}
