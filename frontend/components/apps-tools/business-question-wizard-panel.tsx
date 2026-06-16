"use client";

import { BarChart3, Loader2, Sparkles } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

type AnalyticsSourceId = "ga4" | "google_sheets" | "warehouse_mcp" | "hivemind";
type DateRangePreset = "last_7d" | "last_30d" | "last_90d" | "mtd" | "qtd" | "custom";

interface SourceOption {
  id: AnalyticsSourceId;
  label: string;
}

interface DatePresetOption {
  id: DateRangePreset;
  label: string;
}

interface QuestionWizardSnapshot {
  enabled: boolean;
  min_question_chars: number;
  template_id: string;
  source_options: SourceOption[];
  date_range_presets: DatePresetOption[];
  default_sources: AnalyticsSourceId[];
  operator_hint: string;
}

interface QuestionPreview {
  ok: boolean;
  title: string;
  date_range_label: string;
  date_start: string;
  date_end: string;
  sources: AnalyticsSourceId[];
  brief_markdown: string;
  session_goal_preview: string;
}

interface QuestionSubmitResponse {
  ok: boolean;
  task_id: string;
  deliverable_id: string;
  title: string;
  href: string;
  session_href: string | null;
  message: string;
}

export function BusinessQuestionWizardPanel(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<QuestionWizardSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [question, setQuestion] = useState("");
  const [title, setTitle] = useState("");
  const [datePreset, setDatePreset] = useState<DateRangePreset>("last_30d");
  const [dateStart, setDateStart] = useState("");
  const [dateEnd, setDateEnd] = useState("");
  const [sources, setSources] = useState<AnalyticsSourceId[]>(["ga4", "hivemind"]);
  const [dispatchSession, setDispatchSession] = useState(true);
  const [preview, setPreview] = useState<QuestionPreview | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [lastResult, setLastResult] = useState<QuestionSubmitResponse | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<QuestionWizardSnapshot>("analytics-workspace/question-wizard");
      setSnapshot(data);
      if (data.default_sources?.length) {
        setSources(data.default_sources);
      }
    } catch {
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const buildBody = useCallback(() => {
    const trimmed = question.trim();
    const body: Record<string, unknown> = {
      business_question: trimmed,
      date_range_preset: datePreset,
      sources,
      title: title.trim() || null,
    };
    if (datePreset === "custom") {
      body.date_start = dateStart || null;
      body.date_end = dateEnd || null;
    }
    return body;
  }, [dateEnd, datePreset, dateStart, question, sources, title]);

  const runPreview = useCallback(async () => {
    const min = snapshot?.min_question_chars ?? 12;
    if (question.trim().length < min) {
      setPreview(null);
      return;
    }
    if (datePreset === "custom" && (!dateStart || !dateEnd)) {
      setPreview(null);
      return;
    }
    setPreviewing(true);
    try {
      const data = await hivePostJson<QuestionPreview>(
        "analytics-workspace/question-wizard/preview",
        buildBody(),
      );
      setPreview(data);
    } catch (e) {
      setPreview(null);
      toast.error(e instanceof HiveApiError ? e.message : "Preview failed");
    } finally {
      setPreviewing(false);
    }
  }, [buildBody, dateEnd, datePreset, dateStart, question, snapshot?.min_question_chars]);

  useEffect(() => {
    const timer = window.setTimeout(() => void runPreview(), 500);
    return () => window.clearTimeout(timer);
  }, [runPreview]);

  const toggleSource = (id: AnalyticsSourceId): void => {
    setSources((prev) => {
      if (prev.includes(id)) {
        const next = prev.filter((s) => s !== id);
        return next.length ? next : prev;
      }
      return [...prev, id];
    });
  };

  const submit = useCallback(async () => {
    const min = snapshot?.min_question_chars ?? 12;
    if (question.trim().length < min) {
      toast.error(`Question must be at least ${min} characters.`);
      return;
    }
    setSubmitting(true);
    try {
      const data = await hivePostJson<QuestionSubmitResponse>(
        "analytics-workspace/question-wizard/submit",
        { ...buildBody(), dispatch_session: dispatchSession },
      );
      setLastResult(data);
      toast.success(data.message || "Analytics brief dispatched");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Dispatch failed");
    } finally {
      setSubmitting(false);
    }
  }, [buildBody, dispatchSession, question, snapshot?.min_question_chars]);

  if (loading) {
    return (
      <V4Card className="border-cyan/20" data-testid="analytics-question-wizard-loading">
        <div className="flex items-center gap-2 p-4 text-sm text-(--qs-text-3)">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          Loading Business Question wizard…
        </div>
      </V4Card>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  const minChars = snapshot.min_question_chars;

  return (
    <V4Card
      id="analytics-question-wizard"
      className="border-cyan/30"
      data-testid="analytics-question-wizard"
    >
      <V4CardHeader
        kicker="DA4 · Business question"
        title="Question → analytics session"
        description={snapshot.operator_hint}
        actions={<V4Badge tone="info">{snapshot.template_id}</V4Badge>}
      />
      <div className="space-y-4 px-4 pb-4">
        <label className="block text-sm">
          <span className="font-medium text-(--qs-text)">Business question</span>
          <span className="mt-0.5 block text-xs text-(--qs-text-3)">
            What decision should this report support? (min {minChars} chars)
          </span>
          <textarea
            className="qs-input mt-2 min-h-[88px] w-full text-sm"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Why did organic signups drop 18% WoW while paid CAC held flat?"
            data-testid="analytics-question-input"
          />
        </label>

        <label className="block text-sm">
          <span className="text-(--qs-text-2)">Brief title (optional)</span>
          <input
            className="qs-input mt-1 w-full"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Q2 signup funnel review"
          />
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="text-(--qs-text-2)">Date range</span>
            <QsSelect
              className="mt-1"
              value={datePreset}
              onValueChange={(v) => setDatePreset(v as DateRangePreset)}
              options={snapshot.date_range_presets.map((p) => ({ value: p.id, label: p.label }))}
              aria-label="Date range preset"
            />
          </label>
          {datePreset === "custom" ? (
            <div className="grid grid-cols-2 gap-2">
              <label className="block text-sm">
                <span className="text-(--qs-text-2)">Start</span>
                <input
                  type="date"
                  className="qs-input mt-1 w-full"
                  value={dateStart}
                  onChange={(e) => setDateStart(e.target.value)}
                />
              </label>
              <label className="block text-sm">
                <span className="text-(--qs-text-2)">End</span>
                <input
                  type="date"
                  className="qs-input mt-1 w-full"
                  value={dateEnd}
                  onChange={(e) => setDateEnd(e.target.value)}
                />
              </label>
            </div>
          ) : null}
        </div>

        <fieldset className="text-sm">
          <legend className="mb-2 font-medium text-(--qs-text)">Data sources (read-only)</legend>
          <div className="flex flex-wrap gap-2">
            {snapshot.source_options.map((opt) => {
              const active = sources.includes(opt.id);
              return (
                <button
                  key={opt.id}
                  type="button"
                  className={`qs-btn qs-btn--sm ${active ? "qs-btn--primary" : "qs-btn--ghost"}`}
                  onClick={() => toggleSource(opt.id)}
                  aria-pressed={active}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </fieldset>

        {previewing ? (
          <p className="flex items-center gap-2 text-xs text-(--qs-text-3)">
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
            Previewing brief…
          </p>
        ) : null}

        {preview ? (
          <div
            className="rounded-lg border border-white/10 bg-black/25 p-3 text-xs font-mono text-(--qs-text-2)"
            data-testid="analytics-question-preview"
          >
            <p className="mb-2 font-sans text-sm font-medium text-(--qs-text)">{preview.title}</p>
            <p className="mb-2 font-sans text-xs text-cyan">{preview.date_range_label}</p>
            <pre className="max-h-40 overflow-auto whitespace-pre-wrap">{preview.brief_markdown.slice(0, 600)}</pre>
          </div>
        ) : null}

        <label className="flex items-center gap-2 text-sm text-(--qs-text-2)">
          <input
            type="checkbox"
            checked={dispatchSession}
            onChange={(e) => setDispatchSession(e.target.checked)}
          />
          Dispatch business-analytics-report supervisor session after save
        </label>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="qs-btn qs-btn--primary"
            disabled={submitting || question.trim().length < minChars}
            onClick={() => void submit()}
            data-testid="analytics-question-submit"
          >
            {submitting ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <Sparkles className="h-4 w-4" aria-hidden />
            )}
            Dispatch analytics brief
          </button>
        </div>

        {lastResult ? (
          <p className="text-sm text-(--qs-success)">
            {lastResult.message}{" "}
            <Link href={lastResult.href} className="underline">
              Open task
            </Link>
            {lastResult.session_href ? (
              <>
                {" · "}
                <Link href={lastResult.session_href} className="underline">
                  Analytics session
                </Link>
              </>
            ) : null}
          </p>
        ) : null}

        <p className="text-xs text-(--qs-text-3)">
          <BarChart3 className="mr-1 inline h-3.5 w-3.5 text-cyan" aria-hidden />
          Mission Kanban lineage + critic rubric ≥4/5 before export simulate.
        </p>
      </div>
    </V4Card>
  );
}
