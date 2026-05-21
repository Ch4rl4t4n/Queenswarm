"use client";

import Link from "next/link";
import { Mic, Play } from "lucide-react";

import { V4Badge } from "@/components/ui/v4/v4-badge";

interface V4QueenMissionProps {
  brief: string;
  onBriefChange: (value: string) => void;
  onRun: () => void;
  busy: boolean;
  error: string | null;
}

/** Queen mission action banner — directly under Agents on dashboard. */
export function V4QueenMission({ brief, onBriefChange, onRun, busy, error }: V4QueenMissionProps) {
  return (
    <section id="hive-task" className="v4-action-banner scroll-mt-28">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-pollen">Queen mission</h2>
          <p className="mt-1 text-sm text-(--qs-text-3)">
            Submit a brief — the 7-step flow runs and Ballroom opens with live transcript &amp; voice.
          </p>
        </div>
        <V4Badge tone="gold">7-step flow</V4Badge>
      </div>
      <textarea
        className="v4-textarea mt-5 min-h-[120px]"
        value={brief}
        onChange={(e) => onBriefChange(e.target.value)}
        placeholder="What should the hive do? e.g. Research top 5 voice-AI competitors, evaluate, and draft a positioning memo."
        aria-label="Queen mission brief"
      />
      {error ? <p className="mt-2 text-sm text-(--qs-red)">{error}</p> : null}
      <div className="mt-4 flex flex-col gap-3">
        <p className="text-xs text-(--qs-text-3)">
          <Link href="/tasks/new" className="text-(--qs-cyan) hover:text-pollen">
            Open full New-task screen
          </Link>
          {" "}
          (step preview · recipe · submit)
        </p>
        <div className="flex w-full items-center justify-between gap-3">
          <Link href="/ballroom" className="qs-btn qs-btn--ghost qs-btn--sm shrink-0 gap-2">
            <Mic className="h-4 w-4" aria-hidden />
            Voice brief
          </Link>
          <button type="button" className="qs-btn qs-btn--primary qs-btn--sm shrink-0 gap-2" disabled={busy} onClick={onRun}>
            <Play className="h-4 w-4" aria-hidden />
            {busy ? "Processing…" : "Run mission"}
          </button>
        </div>
      </div>
    </section>
  );
}
