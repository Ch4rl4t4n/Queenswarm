"use client";

import { Loader2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { QsSelect } from "@/components/ui/qs-select";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { RubricTemplateRow } from "@/lib/hive-types";

interface LoopTurn {
  turn: number;
  score: number;
  is_valid: boolean;
  passed: boolean;
  feedback: string;
}

interface ClosedReviewLoopResult {
  ok: boolean;
  passed: boolean;
  turns_used: number;
  max_turns: number;
  min_score_label: string;
  template_name: string;
  final_text: string;
  iterations: LoopTurn[];
  message: string;
}

/** LOOP1 — rubric score → self-heal → re-run until pass or max turns. */
export function ClosedReviewLoopPanel(): JSX.Element {
  const [templates, setTemplates] = useState<RubricTemplateRow[]>([]);
  const [templateId, setTemplateId] = useState("marketing-creative");
  const [draft, setDraft] = useState(
    "Launch your next campaign — verified agent swarms ship faster. Click to learn more.",
  );
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ClosedReviewLoopResult | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [rows, presets] = await Promise.all([
        hiveGet<RubricTemplateRow[]>("harness/rubric-templates"),
        hiveGet<{ active_rubric_template_id: string | null }>("solo-operator/closed-loop-presets").catch(
          () => ({ active_rubric_template_id: null }),
        ),
      ]);
      setTemplates(rows);
      const activeTemplate = presets.active_rubric_template_id;
      if (activeTemplate && rows.some((row) => row.id === activeTemplate)) {
        setTemplateId(activeTemplate);
      } else if (rows.length > 0 && !rows.some((row) => row.id === templateId)) {
        setTemplateId(rows[0]?.id ?? "copy-marketing");
      }
    } catch {
      setTemplates([]);
    } finally {
      setLoading(false);
    }
  }, [templateId]);

  useEffect(() => {
    void load();
  }, [load]);

  const runLoop = useCallback(async () => {
    const text = draft.trim();
    if (text.length < 8) {
      toast.error("Draft must be at least 8 characters.");
      return;
    }
    setBusy(true);
    try {
      const data = await hivePostJson<ClosedReviewLoopResult>("harness/closed-review-loop/run", {
        template_id: templateId,
        text,
      });
      setResult(data);
      toast.success(data.passed ? "Closed loop PASS" : "Closed loop exhausted turns");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Closed review loop failed");
    } finally {
      setBusy(false);
    }
  }, [draft, templateId]);

  if (loading) {
    return (
      <V4Card className="mt-4 flex items-center gap-2 p-4 text-sm text-white/60">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Loading closed review loop…
      </V4Card>
    );
  }

  return (
    <V4Card id="harness-closed-review-loop" className="mt-4 border-pollen/30">
      <V4CardHeader
        kicker="LOOP1"
        title="Closed review loop"
        description="Rubric score → self-heal revision → re-run until pass or LOOP2 max turns."
      />
      <div className="space-y-3 px-4 pb-4">
        <label className="block text-sm text-white/60">Rubric template</label>
        <QsSelect
          value={templateId}
          onValueChange={setTemplateId}
          options={templates.map((row) => ({ value: row.id, label: row.name }))}
          aria-label="Rubric template"
        />
        <label className="block text-sm">
          <span className="text-white/60">Draft to review</span>
          <textarea
            className="qs-input mt-1 min-h-[96px] w-full font-mono text-sm"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
        </label>
        <button
          type="button"
          className="qs-btn qs-btn--primary qs-btn--sm inline-flex gap-1.5"
          disabled={busy}
          onClick={() => void runLoop()}
        >
          {busy ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
          Run closed loop
        </button>
        {result ? (
          <div className="rounded-md border border-white/10 bg-black/25 p-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              {result.passed ? <V4Badge tone="ok">Pass</V4Badge> : <V4Badge tone="warn">Needs work</V4Badge>}
              <span className="font-mono text-xs text-cyan">
                {result.turns_used}/{result.max_turns} turns · min {result.min_score_label}
              </span>
              <span className="text-white/60">{result.template_name}</span>
            </div>
            <p className="mt-2 text-white/80">{result.message}</p>
            <ul className="mt-2 space-y-1 text-xs text-white/60">
              {result.iterations.map((row) => (
                <li key={row.turn}>
                  Turn {row.turn}: {Math.round(row.score * 100)}% — {row.passed ? "pass" : "revise"}
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs font-semibold uppercase text-white/40">Final draft</p>
            <p className="mt-1 whitespace-pre-wrap font-mono text-xs text-(--qs-text-2)">{result.final_text}</p>
          </div>
        ) : null}
      </div>
    </V4Card>
  );
}
