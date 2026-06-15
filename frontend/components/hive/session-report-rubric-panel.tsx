"use client";

import Link from "next/link";
import { ClipboardCheck, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { V4Badge, V4Card } from "@/components/ui/v4";
import { hiveGet } from "@/lib/api";
import { cn } from "@/lib/utils";

interface SessionReportRubricDimension {
  id: string;
  label: string;
  weight_pct: number;
  prompt: string;
}

interface SessionReportRubricState {
  enabled: boolean;
  visible: boolean;
  session_id: string;
  session_status: string;
  pending_approval: boolean;
  template_id: string;
  template_name: string;
  template_category: string;
  pass_threshold_pct: number;
  score: number | null;
  score_label: string | null;
  min_score_label: string;
  passed: boolean | null;
  pre_approve_status: "ready" | "below_floor" | "pending" | "unknown";
  feedback: string | null;
  deliverable_preview: string;
  dimensions: SessionReportRubricDimension[];
  must_satisfy: string[];
  operator_hint: string;
  evaluate_href: string;
}

interface SessionReportRubricPanelProps {
  sessionId: string;
  sessionStatus?: string;
}

function statusTone(status: SessionReportRubricState["pre_approve_status"]): string {
  if (status === "ready") {
    return "border-success/35 bg-success/5";
  }
  if (status === "below_floor") {
    return "border-(--qs-red)/35 bg-(--qs-red)/5";
  }
  if (status === "pending") {
    return "border-pollen/35 bg-pollen/5";
  }
  return "border-(--qs-border) bg-black/15";
}

/** TR3 — Rubric score before operator approve in session report. */
export function SessionReportRubricPanel({
  sessionId,
  sessionStatus,
}: SessionReportRubricPanelProps): JSX.Element | null {
  const [state, setState] = useState<SessionReportRubricState | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await hiveGet<SessionReportRubricState>(
        `agents/sessions/${encodeURIComponent(sessionId)}/report-rubric`,
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
        Loading rubric score…
      </div>
    );
  }

  if (!state?.enabled || !state.visible) {
    return null;
  }

  const emphasize = sessionStatus === "needs_input" || state.pending_approval;

  return (
    <V4Card
      className={cn("p-3", statusTone(state.pre_approve_status), emphasize && "ring-1 ring-pollen/25")}
      data-testid="session-report-rubric-panel"
      id="session-report-rubric"
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <ClipboardCheck className="size-4 text-pollen" aria-hidden />
        <span className="text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">Rubric pre-approve</span>
        <V4Badge tone="gold">TR3</V4Badge>
        <V4Badge tone="info">{state.template_name}</V4Badge>
        {state.passed ? (
          <V4Badge tone="ok">Pass</V4Badge>
        ) : state.passed === false ? (
          <V4Badge tone="err">Below floor</V4Badge>
        ) : (
          <V4Badge tone="warn">Pending</V4Badge>
        )}
      </div>

      <div className="mb-3 grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-(--qs-text-4)">Score</p>
          <p className="mt-1 font-mono text-xl font-bold text-pollen">{state.score_label ?? "—"}</p>
          <p className="text-[11px] text-(--qs-text-3)">min {state.min_score_label}</p>
        </div>
        <div className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-(--qs-text-4)">Template gate</p>
          <p className="mt-1 font-mono text-xl font-bold text-success">{state.pass_threshold_pct}%</p>
          <p className="text-[11px] text-(--qs-text-3)">{state.template_category}</p>
        </div>
        <div className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-(--qs-text-4)">Pre-approve</p>
          <p className="mt-1 text-sm font-semibold capitalize text-(--qs-text)">{state.pre_approve_status.replace("_", " ")}</p>
        </div>
      </div>

      {state.feedback ? <p className="mb-3 text-xs text-(--qs-text-2)">{state.feedback}</p> : null}

      {state.deliverable_preview ? (
        <p className="mb-3 rounded-md border border-(--qs-border)/70 bg-black/25 px-3 py-2 text-xs text-(--qs-text-2)">
          {state.deliverable_preview}
        </p>
      ) : null}

      {state.must_satisfy.length > 0 ? (
        <ul className="mb-3 space-y-1 text-xs text-(--qs-text-2)">
          {state.must_satisfy.map((item) => (
            <li key={item} className="flex gap-2">
              <span className="text-success">✓</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      ) : null}

      {state.dimensions.length > 0 ? (
        <div className="mb-3 space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-(--qs-text-4)">Dimensions</p>
          {state.dimensions.map((dim) => (
            <div key={dim.id} className="rounded-md border border-(--qs-border)/60 px-2.5 py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium text-(--qs-text)">{dim.label}</span>
                <span className="font-mono text-[10px] text-cyan">{dim.weight_pct}%</span>
              </div>
              <p className="mt-1 text-[11px] text-(--qs-text-3)">{dim.prompt}</p>
            </div>
          ))}
        </div>
      ) : null}

      <p className="text-xs text-(--qs-text-3)">{state.operator_hint}</p>

      {state.pre_approve_status !== "ready" ? (
        <Link href={state.evaluate_href} className="qs-btn qs-btn--ghost qs-btn--sm mt-3 inline-flex">
          Open harness rubrics
        </Link>
      ) : null}
    </V4Card>
  );
}
