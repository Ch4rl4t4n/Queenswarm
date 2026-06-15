"use client";

import { ChevronDown, ChevronUp, LineChart, Loader2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

interface ThesisQuestion {
  id: string;
  title: string;
  prompt: string;
  hint: string;
}

interface ThesisSnapshot {
  enabled: boolean;
  questions: ThesisQuestion[];
  min_answer_chars: number;
  paper_cockpit_href: string;
  live_gate_skill: string;
}

interface ThesisSubmitResponse {
  ok: boolean;
  task_id: string;
  title: string;
  href: string;
  session_href: string | null;
  paper_cockpit_href: string;
  message: string;
}

export function TradingThesisWizardPanel(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<ThesisSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [briefTitle, setBriefTitle] = useState("");
  const [dispatchSession, setDispatchSession] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [lastResult, setLastResult] = useState<ThesisSubmitResponse | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<ThesisSnapshot>("solo-operator/trading-thesis-wizard");
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
      const data = await hivePostJson<ThesisSubmitResponse>(
        "solo-operator/trading-thesis-wizard/submit",
        {
          answers,
          title: briefTitle.trim() || null,
          dispatch_session: dispatchSession,
        },
      );
      setLastResult(data);
      toast.success(data.message || "Thesis brief saved");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Submit failed";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  }, [answers, briefTitle, dispatchSession, snapshot?.questions.length]);

  if (loading) {
    return (
      <V4Card className="mb-4 flex items-center gap-2 p-4 text-sm text-white/60">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Loading thesis wizard…
      </V4Card>
    );
  }

  if (!snapshot?.enabled || snapshot.questions.length === 0) {
    return null;
  }

  return (
    <V4Card className="mb-4 max-lg:mb-3 border-cyan-500/30" id="trading-thesis-wizard">
      <V4CardHeader
        kicker="NP5 · Trading thesis"
        title="Trading thesis brief"
        description="Calibrated beliefs before live stake — real-money-risk-gate required."
        actions={
          <div className="flex items-center gap-2">
            <V4Badge tone="info">{snapshot.live_gate_skill}</V4Badge>
            <HiveRefreshButton busy={loading} onClick={() => void load()} />
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1"
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
            >
              {open ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
              {open ? "Collapse" : "Expand"}
            </button>
          </div>
        }
      />
      {open ? (
        <div className="space-y-4 px-4 pb-4">
          <p className="text-sm text-white/70">
            Probabilities not guesses — complete all fields before paper or live lanes.{" "}
            <Link href={snapshot.paper_cockpit_href} className="text-[#00FFFF] hover:underline">
              Paper cockpit
            </Link>
          </p>
          <label className="block text-sm">
            <span className="text-white/60">Brief title (optional)</span>
            <input
              className="qs-input mt-1 w-full"
              value={briefTitle}
              onChange={(e) => setBriefTitle(e.target.value)}
              placeholder="Fed rate cut thesis Q3"
            />
          </label>
          {snapshot.questions.map((q) => (
            <label key={q.id} className="block text-sm">
              <span className="font-medium text-white">{q.title}</span>
              <span className="mt-0.5 block text-white/60">{q.prompt}</span>
              {q.hint ? <span className="text-xs text-white/40">{q.hint}</span> : null}
              <textarea
                className="qs-input mt-2 min-h-[72px] w-full font-mono text-sm"
                value={answers[q.id] ?? ""}
                onChange={(e) => setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))}
              />
            </label>
          ))}
          <label className="flex items-center gap-2 text-sm text-white/80">
            <input
              type="checkbox"
              checked={dispatchSession}
              onChange={(e) => setDispatchSession(e.target.checked)}
            />
            Start polymarket-prediction-evaluator session after save
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="qs-btn qs-btn--primary"
              disabled={submitting}
              onClick={() => void submit()}
            >
              {submitting ? <Loader2 className="size-4 animate-spin" /> : <LineChart className="size-4" />}
              Save thesis brief
            </button>
          </div>
          {lastResult ? (
            <p className="text-sm text-[#00FF88]">
              Saved —{" "}
              <Link href={lastResult.href} className="underline">
                open task
              </Link>
              {lastResult.session_href ? (
                <>
                  {" · "}
                  <Link href={lastResult.session_href} className="underline">
                    evaluator session
                  </Link>
                </>
              ) : null}
            </p>
          ) : null}
        </div>
      ) : (
        <p className="px-4 pb-4 text-sm text-white/60">
          6 prompts: market · implied prob · edge · size cap · kill criteria · paper preflight
        </p>
      )}
    </V4Card>
  );
}
