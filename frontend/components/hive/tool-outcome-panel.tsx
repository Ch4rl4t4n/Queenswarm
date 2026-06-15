"use client";

import { AlertTriangle, CheckCircle2, Loader2, Wrench } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { V4Badge, V4Card } from "@/components/ui/v4";
import { hiveGet } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface ToolOutcomeEntryState {
  tool_name: string;
  connector_slug: string | null;
  mode: string;
  risk_tier: string | null;
  args_summary: string;
  result_summary: string;
  simulated: boolean | null;
  executed: boolean | null;
  sub_agent_role: string | null;
  event_type: string;
  occurred_at: string | null;
}

export interface CriticOutcomeState {
  score: number | null;
  score_label: string | null;
  min_score_label: string | null;
  passed: boolean | null;
  feedback: string | null;
  source: string | null;
}

export interface ToolOutcomePanelState {
  enabled: boolean;
  session_id: string;
  session_status: string;
  visible: boolean;
  pending_approval: boolean;
  approval_reason: string | null;
  tools: ToolOutcomeEntryState[];
  critic: CriticOutcomeState | null;
  operator_action: string;
}

interface ToolOutcomePanelProps {
  sessionId: string;
  sessionStatus?: string;
}

function modeTone(mode: string): "ok" | "warn" | "info" | "gold" {
  const key = mode.trim().toLowerCase();
  if (key === "live") return "warn";
  if (key === "simulate" || key === "draft") return "ok";
  return "info";
}

/** AL2 — Tool evidence panel for needs_input / approve decisions. */
export function ToolOutcomePanel({ sessionId, sessionStatus }: ToolOutcomePanelProps): JSX.Element | null {
  const [state, setState] = useState<ToolOutcomePanelState | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await hiveGet<ToolOutcomePanelState>(
        `agents/sessions/${encodeURIComponent(sessionId)}/tool-outcomes`,
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
        Loading tool outcomes…
      </div>
    );
  }

  if (!state?.enabled || !state.visible) {
    return null;
  }

  const emphasize = sessionStatus === "needs_input";

  return (
    <V4Card
      className={cn(
        "p-3",
        emphasize ? "border-[#FF00AA]/35 bg-[#FF00AA]/5" : "border-pollen/25 bg-pollen/5",
      )}
      id="tool-outcome-panel"
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Wrench className="size-4 text-cyan" aria-hidden />
        <span className="text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">Tool outcomes</span>
        {state.pending_approval ? <V4Badge tone="warn">Approval gate</V4Badge> : null}
        {emphasize ? <V4Badge tone="warn">Verify now</V4Badge> : null}
      </div>

      <p className="mb-3 text-xs text-(--qs-text-2)">{state.operator_action}</p>

      {state.approval_reason ? (
        <p className="mb-3 flex items-start gap-1.5 text-xs text-[#FFB800]">
          <AlertTriangle className="mt-0.5 size-3 shrink-0" aria-hidden />
          {state.approval_reason}
        </p>
      ) : null}

      {state.critic ? (
        <div
          className={cn(
            "mb-3 rounded-lg border px-3 py-2",
            state.critic.passed ? "border-[#00FF88]/30 bg-[#00FF88]/5" : "border-[#FFB800]/30 bg-[#FFB800]/5",
          )}
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-(--qs-text-3)">Critic</span>
            {state.critic.score_label ? (
              <span className="font-mono text-xs text-pollen">{state.critic.score_label}</span>
            ) : null}
            {state.critic.min_score_label ? (
              <span className="font-mono text-[10px] text-(--qs-text-3)">min {state.critic.min_score_label}</span>
            ) : null}
            {state.critic.passed ? (
              <V4Badge tone="ok">Pass</V4Badge>
            ) : state.critic.passed === false ? (
              <V4Badge tone="warn">Below floor</V4Badge>
            ) : null}
          </div>
          {state.critic.feedback ? (
            <p className="mt-1.5 text-xs text-(--qs-text-2)">{state.critic.feedback}</p>
          ) : null}
        </div>
      ) : null}

      {state.tools.length > 0 ? (
        <ul className="space-y-2">
          {state.tools.map((tool) => (
            <li
              key={`${tool.tool_name}-${tool.event_type}-${tool.occurred_at ?? tool.sub_agent_role ?? "row"}`}
              className="rounded-lg border border-(--qs-border) bg-black/25 px-3 py-2"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold text-(--qs-text)">{tool.tool_name}</span>
                {tool.connector_slug ? (
                  <span className="font-mono text-[10px] text-cyan">{tool.connector_slug}</span>
                ) : null}
                <V4Badge tone={modeTone(tool.mode)}>{tool.mode}</V4Badge>
                {tool.risk_tier ? <V4Badge tone="gold">{tool.risk_tier}</V4Badge> : null}
                {tool.simulated ? <V4Badge tone="ok">simulated</V4Badge> : null}
                {tool.executed ? <V4Badge tone="warn">executed</V4Badge> : null}
              </div>
              {tool.sub_agent_role ? (
                <p className="mt-1 text-[10px] uppercase tracking-wide text-(--qs-text-3)">{tool.sub_agent_role}</p>
              ) : null}
              <p className="mt-1 font-mono text-[10px] text-(--qs-text-3)">args: {tool.args_summary}</p>
              {tool.result_summary ? (
                <p className="mt-1 text-xs text-(--qs-text-2)">{tool.result_summary}</p>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="flex items-center gap-1.5 text-xs text-(--qs-text-3)">
          <CheckCircle2 className="size-3 shrink-0" aria-hidden />
          No tool events yet — sub-agent lanes may still be planning.
        </p>
      )}
    </V4Card>
  );
}
