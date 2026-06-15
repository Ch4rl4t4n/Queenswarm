"use client";

import { HelpCircle, Loader2, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { V4Badge, V4Card } from "@/components/ui/v4";
import { agenticPatternLabel } from "@/lib/agentic-pattern-labels";
import { hiveGet } from "@/lib/api";
import { cn } from "@/lib/utils";

export type ExplainerPhaseId = "goal" | "plan" | "tool" | "verify";

export interface PatternToolExplainerChipState {
  chip_id: string;
  phase_id: ExplainerPhaseId | null;
  phase_label: string | null;
  sub_agent_role: string | null;
  pattern_id: string;
  pattern_label: string;
  tool_name: string | null;
  tool_label: string | null;
  explainer: string;
}

export interface PatternToolExplainerState {
  enabled: boolean;
  visible: boolean;
  session_id: string;
  session_status: string;
  chips: PatternToolExplainerChipState[];
  pattern_rationale: string[];
  operator_hint: string;
}

interface PatternToolExplainerPanelProps {
  sessionId: string;
  sessionStatus?: string;
}

function chipTone(chip: PatternToolExplainerChipState): string {
  if (chip.phase_id === "verify") {
    return "border-pollen/35 bg-pollen/5";
  }
  if (chip.phase_id === "tool" || chip.sub_agent_role) {
    return "border-cyan/30 bg-cyan/5";
  }
  return "border-(--qs-border) bg-black/20";
}

/** AL4 — Pattern + tool explainer chips per loop phase / sub-agent step. */
export function PatternToolExplainerPanel({
  sessionId,
  sessionStatus,
}: PatternToolExplainerPanelProps): JSX.Element | null {
  const [state, setState] = useState<PatternToolExplainerState | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await hiveGet<PatternToolExplainerState>(
        `agents/sessions/${encodeURIComponent(sessionId)}/step-explainers`,
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
        Loading step explainers…
      </div>
    );
  }

  if (!state?.enabled || !state.visible || state.chips.length === 0) {
    return null;
  }

  const phaseChips = state.chips.filter((chip) => chip.phase_id);
  const subChips = state.chips.filter((chip) => chip.sub_agent_role && !chip.phase_id);

  return (
    <V4Card className="border-pollen/20 p-3" id="pattern-tool-explainer" data-testid="pattern-tool-explainer-panel">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Sparkles className="size-4 text-pollen" aria-hidden />
        <span className="text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">Why this tool</span>
        <V4Badge tone="gold">AL4</V4Badge>
      </div>
      <p className="mb-3 text-xs text-(--qs-text-3)">{state.operator_hint}</p>

      {phaseChips.length > 0 ? (
        <div className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-text-4)">Loop phases</p>
          <ul className="grid gap-2 sm:grid-cols-2">
            {phaseChips.map((chip) => (
              <li
                key={chip.chip_id}
                className={cn("rounded-lg border px-3 py-2", chipTone(chip))}
                data-testid={`explainer-chip-${chip.phase_id}`}
              >
                <div className="flex flex-wrap items-center gap-1.5">
                  <V4Badge tone="info">{chip.phase_label ?? chip.phase_id}</V4Badge>
                  <V4Badge tone="gold">{agenticPatternLabel(chip.pattern_id)}</V4Badge>
                  {chip.tool_label ? (
                    <span className="font-mono text-[10px] text-cyan">{chip.tool_label}</span>
                  ) : null}
                </div>
                <p className="mt-1.5 flex gap-1.5 text-xs text-(--qs-text-2)">
                  <HelpCircle className="mt-0.5 size-3 shrink-0 text-(--qs-text-4)" aria-hidden />
                  {chip.explainer}
                </p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {subChips.length > 0 ? (
        <div className={cn("space-y-2", phaseChips.length > 0 && "mt-3")}>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-text-4)">Sub-agent lanes</p>
          <ul className="flex flex-wrap gap-2">
            {subChips.map((chip) => (
              <li
                key={chip.chip_id}
                className={cn("min-w-[140px] flex-1 rounded-lg border px-3 py-2 sm:max-w-[240px]", chipTone(chip))}
                data-testid={`explainer-chip-sub-${chip.sub_agent_role}`}
              >
                <div className="flex flex-wrap items-center gap-1.5">
                  <V4Badge tone="info">{chip.sub_agent_role}</V4Badge>
                  <V4Badge tone="gold">{agenticPatternLabel(chip.pattern_id)}</V4Badge>
                </div>
                {chip.tool_label ? (
                  <p className="mt-1 font-mono text-[10px] text-cyan">{chip.tool_label}</p>
                ) : null}
                <p className="mt-1 text-[11px] text-(--qs-text-3)">{chip.explainer}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {state.pattern_rationale.length > 0 ? (
        <details className="mt-3 rounded-md border border-(--qs-border) bg-black/15 px-3 py-2 text-xs text-(--qs-text-3)">
          <summary className="cursor-pointer font-medium text-(--qs-text-2)">Pattern Router rationale</summary>
          <ul className="mt-2 list-disc space-y-1 pl-4">
            {state.pattern_rationale.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </V4Card>
  );
}
