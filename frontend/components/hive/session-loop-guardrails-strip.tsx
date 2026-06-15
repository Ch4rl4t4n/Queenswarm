"use client";

import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { V4Badge, V4Card } from "@/components/ui/v4";
import { hiveGet } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface SessionLoopGuardrailsState {
  enabled: boolean;
  status: "healthy" | "warn" | "halt";
  max_turns: number;
  turns_used: number;
  min_score_label: string;
  last_rubric_score: number | null;
  cost_cap_usd: number;
  spent_usd: number;
  cost_utilization: number;
  alerts: string[];
  next_operator_action: string;
}

interface SessionLoopGuardrailsStripProps {
  sessionId: string;
  sessionStatus?: string;
}

function toneClass(status: SessionLoopGuardrailsState["status"]): string {
  if (status === "halt") {
    return "border-[#FF3366]/40 bg-[#FF3366]/5";
  }
  if (status === "warn") {
    return "border-[#FFB800]/35 bg-[#FFB800]/5";
  }
  return "border-[#00FF88]/25 bg-[#00FF88]/5";
}

export function SessionLoopGuardrailsStrip({
  sessionId,
  sessionStatus,
}: SessionLoopGuardrailsStripProps): JSX.Element | null {
  const [state, setState] = useState<SessionLoopGuardrailsState | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await hiveGet<SessionLoopGuardrailsState>(
        `agents/sessions/${encodeURIComponent(sessionId)}/loop-guardrails`,
      );
      setState(data);
    } catch {
      setState(null);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!sessionStatus || !["running", "queued", "needs_input"].includes(sessionStatus)) {
      return;
    }
    const timer = window.setInterval(() => void load(), 10000);
    return () => window.clearInterval(timer);
  }, [load, sessionStatus]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-(--qs-text-3)">
        <Loader2 className="size-3 animate-spin" aria-hidden />
        Loading loop guardrails…
      </div>
    );
  }

  if (!state?.enabled) {
    return null;
  }

  return (
    <V4Card className={cn("p-3", toneClass(state.status))} id="session-loop-guardrails">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">Loop guardrails</span>
        {state.status === "healthy" ? (
          <V4Badge tone="ok">Healthy</V4Badge>
        ) : state.status === "warn" ? (
          <V4Badge tone="warn">Warn</V4Badge>
        ) : (
          <V4Badge tone="err">Halt</V4Badge>
        )}
        <span className="font-mono text-xs text-cyan">
          turns {state.turns_used}/{state.max_turns}
        </span>
        <span className="font-mono text-xs text-pollen">
          ${state.spent_usd.toFixed(2)}/${state.cost_cap_usd.toFixed(2)}
        </span>
        <span className="font-mono text-xs text-(--qs-text-2)">min {state.min_score_label}</span>
      </div>
      {state.alerts.length > 0 ? (
        <ul className="mt-2 space-y-1 text-xs text-[#FFB800]">
          {state.alerts.map((alert) => (
            <li key={alert} className="flex items-start gap-1.5">
              <AlertTriangle className="mt-0.5 size-3 shrink-0" aria-hidden />
              {alert}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-[#00FF88]">
          <CheckCircle2 className="size-3 shrink-0" aria-hidden />
          Within closed-loop guardrails.
        </p>
      )}
      <p className="mt-2 text-xs text-(--qs-text-2)">{state.next_operator_action}</p>
    </V4Card>
  );
}
