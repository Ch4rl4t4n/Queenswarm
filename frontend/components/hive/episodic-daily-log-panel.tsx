"use client";

import Link from "next/link";
import { CalendarDays, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";

interface EpisodicCaptureRow {
  capture_id: string;
  session_id: string;
  goal: string;
  summary: string;
  captured_at: string;
  href: string | null;
  rubric_score: number | null;
}

interface EpisodicDailyLogDay {
  date: string;
  session_count: number;
  headline: string;
  summary_md: string;
  captures: EpisodicCaptureRow[];
}

interface EpisodicDailyLogState {
  enabled: boolean;
  retention_days: number;
  days: EpisodicDailyLogDay[];
  total_captures: number;
  operator_hint: string;
}

/** MEM1 — Auto episodic capture daily summarized log. */
export function EpisodicDailyLogPanel(): JSX.Element | null {
  const [state, setState] = useState<EpisodicDailyLogState | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<EpisodicDailyLogState>("memory/episodic/daily-log?days=14");
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
      <div className="flex items-center gap-2 text-sm text-(--qs-text-3)">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Loading daily episodic log…
      </div>
    );
  }

  if (!state?.enabled) {
    return null;
  }

  return (
    <V4Card className="border-purple-500/25 bg-purple-500/5" data-testid="episodic-daily-log-panel">
      <V4CardHeader
        leadingIcon={CalendarDays}
        leadingIconTone="purple"
        title="Daily episodic log"
        description="MEM1 — completed sessions auto-capture into a MemSearch-style daily summary."
        hint={sectionHintNode("knowledgeEpisodicDaily")}
        actions={
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void load()}>
            Refresh
          </button>
        }
      />

      <div className="mb-3 flex flex-wrap gap-2">
        <V4Badge tone="gold">MEM1</V4Badge>
        <V4Badge tone="info">{state.total_captures} captures</V4Badge>
        <V4Badge tone="purple">{state.retention_days}d retention</V4Badge>
      </div>

      <p className="mb-3 text-xs text-(--qs-text-3)">{state.operator_hint}</p>

      <div className="space-y-3">
        {state.days.map((day) => (
          <div key={day.date} className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs text-cyan">{day.date}</span>
              <V4Badge tone={day.session_count > 0 ? "ok" : "info"}>{day.session_count} sessions</V4Badge>
            </div>
            <p className="mt-1 text-sm font-medium text-(--qs-text)">{day.headline}</p>
            {day.captures.length > 0 ? (
              <ul className="mt-2 space-y-2">
                {day.captures.map((capture) => (
                  <li key={capture.capture_id} className="text-xs text-(--qs-text-2)">
                    <span className="font-semibold text-(--qs-text)">{capture.goal}</span>
                    <p className="mt-0.5">{capture.summary}</p>
                    {capture.href ? (
                      <Link href={capture.href} className="mt-1 inline-block text-cyan hover:underline">
                        Open session
                      </Link>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-1 text-xs text-(--qs-text-4)">No auto-captures this day.</p>
            )}
          </div>
        ))}
      </div>
    </V4Card>
  );
}
