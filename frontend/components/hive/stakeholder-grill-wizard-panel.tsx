"use client";

import { ChevronDown, ChevronUp, Flame, Loader2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

interface GrillQuestion {
  id: string;
  title: string;
  prompt: string;
  hint: string;
}

interface GrillSnapshot {
  enabled: boolean;
  questions: GrillQuestion[];
  min_answer_chars: number;
}

interface GrillSubmitResponse {
  ok: boolean;
  task_id: string;
  title: string;
  href: string;
  session_href: string | null;
  message: string;
}

interface StakeholderGrillWizardPanelProps {
  onSubmitted?: () => void;
}

export function StakeholderGrillWizardPanel({
  onSubmitted,
}: StakeholderGrillWizardPanelProps): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<GrillSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [briefTitle, setBriefTitle] = useState("");
  const [dispatchSession, setDispatchSession] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [lastResult, setLastResult] = useState<GrillSubmitResponse | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<GrillSnapshot>("solo-operator/grill-wizard");
      setSnapshot(data);
    } catch {
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const submit = useCallback(async () => {
    if (!snapshot?.questions.length) {
      return;
    }
    setSubmitting(true);
    try {
      const data = await hivePostJson<GrillSubmitResponse>("solo-operator/grill-wizard/submit", {
        answers,
        title: briefTitle.trim() || null,
        dispatch_session: dispatchSession,
      });
      setLastResult(data);
      toast.success(data.message || "Brief saved to Kanban");
      onSubmitted?.();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Submit failed");
    } finally {
      setSubmitting(false);
    }
  }, [answers, briefTitle, dispatchSession, onSubmitted, snapshot?.questions.length]);

  if (loading && !snapshot) {
    return (
      <V4Card className="mb-4 max-lg:mb-3">
        <div className="flex items-center gap-2 p-4 text-sm text-(--qs-muted)">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading grill wizard…
        </div>
      </V4Card>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  const minChars = snapshot.min_answer_chars ?? 12;

  return (
    <V4Card className="mb-4 max-lg:mb-3 border-amber-500/30" id="stakeholder-grill-wizard">
      <V4CardHeader
        kicker="NP1 · Stakeholder Grill"
        title="Grill my brief"
        description="Structured interview → markdown artifact in task workspace → optional research session."
        actions={
          <div className="flex items-center gap-2">
            <HiveRefreshButton busy={loading} onClick={() => void load()} />
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1"
              aria-expanded={open}
              onClick={() => setOpen((value) => !value)}
            >
              {open ? (
                <>
                  Collapse
                  <ChevronUp className="size-4" aria-hidden />
                </>
              ) : (
                <>
                  Open wizard
                  <ChevronDown className="size-4" aria-hidden />
                </>
              )}
            </button>
          </div>
        }
      />
      {!open ? (
        <p className="px-4 pb-4 text-xs text-(--qs-text-2)">
          {snapshot.questions.length} prompts · problem · KPI · compliance · kill criteria · verify-first
        </p>
      ) : (
        <div className="space-y-3 px-4 pb-4">
          <label className="block text-xs text-(--qs-text-2)">
            Brief title (optional)
            <input
              className="qs-input mt-1 w-full text-sm"
              value={briefTitle}
              onChange={(e) => setBriefTitle(e.target.value)}
              placeholder="e.g. Mobile pre-approval discovery"
            />
          </label>
          <ul className="space-y-3">
            {snapshot.questions.map((question) => (
              <li
                key={question.id}
                className="rounded-lg border border-(--qs-border) bg-(--qs-surface) p-3"
              >
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-(--qs-text)">{question.title}</span>
                  <V4Badge tone="info">{question.id.replace("_", " ")}</V4Badge>
                </div>
                <p className="mb-2 text-xs text-(--qs-text-2)">{question.prompt}</p>
                {question.hint ? (
                  <p className="mb-2 text-[11px] text-(--qs-muted)">{question.hint}</p>
                ) : null}
                <textarea
                  className="qs-input min-h-[64px] w-full text-sm"
                  value={answers[question.id] ?? ""}
                  onChange={(e) =>
                    setAnswers((prev) => ({
                      ...prev,
                      [question.id]: e.target.value,
                    }))
                  }
                  placeholder={`Min ${minChars} characters…`}
                />
              </li>
            ))}
          </ul>
          <label className="flex cursor-pointer items-center gap-2 text-xs text-(--qs-text-2)">
            <input
              type="checkbox"
              checked={dispatchSession}
              onChange={(e) => setDispatchSession(e.target.checked)}
              className="size-4 rounded border-(--qs-border)"
            />
            Start research session with grill-me after save
          </label>
          <button
            type="button"
            className="qs-btn qs-btn--primary inline-flex items-center gap-2"
            disabled={submitting}
            onClick={() => void submit()}
          >
            {submitting ? (
              <>
                <Loader2 className="size-4 animate-spin" aria-hidden />
                Saving…
              </>
            ) : (
              <>
                <Flame className="size-4 text-amber-400" aria-hidden />
                Save brief to Kanban
              </>
            )}
          </button>
          {lastResult ? (
            <div className="rounded-lg border border-(--qs-border) bg-(--qs-surface-2) p-3 text-xs">
              <p className="mb-2 text-(--qs-text)">{lastResult.message}</p>
              <div className="flex flex-wrap gap-2">
                <Link href={lastResult.href} className="qs-link text-cyan-300">
                  Open task
                </Link>
                {lastResult.session_href ? (
                  <Link href={lastResult.session_href} className="qs-link text-cyan-300">
                    Open session
                  </Link>
                ) : null}
              </div>
            </div>
          ) : null}
        </div>
      )}
    </V4Card>
  );
}
