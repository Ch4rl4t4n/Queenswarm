"use client";

import { Loader2Icon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePutJson } from "@/lib/api";
import { CURATED_MEMORY_MAX_CHARS } from "@/lib/curated-memory-limits";

const INSTRUCTIONS_KIND = "instructions";

/** Tenant behavioral memory — AnswerThis-style operator instructions for Queen harness. */
export function BehavioralMemoryPanel(): JSX.Element {
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const data = await hiveGet<Record<string, string>>("memory/curated");
      setDraft(data[INSTRUCTIONS_KIND] ?? "");
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Behavioral memory unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function save(): Promise<void> {
    setBusy(true);
    try {
      await hivePutJson(`memory/curated/${encodeURIComponent(INSTRUCTIONS_KIND)}`, { content_md: draft });
      toast.success("Behavioral instructions saved");
      await reload();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Save failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <V4Card>
      <V4CardHeader
        kicker="Behavioral memory"
        title="instructions.md"
        description="How Queen should behave — tone, priorities, guardrails. Non-technical operators edit this instead of code."
      />
      {loading ? (
        <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading…
        </p>
      ) : null}
      {err ? <p className="mb-3 text-sm text-(--qs-red)">{err}</p> : null}
      {!loading ? (
        <>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={12}
            maxLength={CURATED_MEMORY_MAX_CHARS}
            className="qs-input min-h-[240px] font-mono text-xs leading-relaxed"
            placeholder={"# Behavioral instructions\n\n- Always verify before reporting to the user\n- Prefer concise morning briefings\n- Flag stalled projects in magenta tone"}
          />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs text-(--qs-text-3)">
              {draft.length}/{CURATED_MEMORY_MAX_CHARS}
            </span>
            <button
              type="button"
              disabled={busy}
              onClick={() => void save()}
              className="qs-btn qs-btn--primary qs-btn--sm"
            >
              {busy ? "Saving…" : "Save instructions"}
            </button>
          </div>
        </>
      ) : null}
    </V4Card>
  );
}
