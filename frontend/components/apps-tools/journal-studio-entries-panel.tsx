"use client";

import { Loader2, NotebookPen, Plus } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";

type EntryOutcome = "win" | "loss" | "breakeven" | "open" | "unknown";

interface JournalTradeEntry {
  id: string;
  source: "manual" | "paper_fill";
  thesis: string;
  outcome: EntryOutcome;
  lesson: string;
  tags: string[];
  mistake_tag: string | null;
  symbol: string | null;
  occurred_at: string;
}

interface JournalEntryList {
  entry_count: number;
  enabled_fields: string[];
  items: JournalTradeEntry[];
  operator_hint: string;
}

const OUTCOME_OPTIONS: { value: EntryOutcome; label: string }[] = [
  { value: "unknown", label: "Unknown" },
  { value: "win", label: "Win" },
  { value: "loss", label: "Loss" },
  { value: "breakeven", label: "Breakeven" },
  { value: "open", label: "Open" },
];

function fieldEnabled(fields: string[], key: string): boolean {
  return fields.includes(key);
}

export function JournalStudioEntriesPanel(): JSX.Element | null {
  const [list, setList] = useState<JournalEntryList | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [thesis, setThesis] = useState("");
  const [lesson, setLesson] = useState("");
  const [outcome, setOutcome] = useState<EntryOutcome>("unknown");
  const [tagsInput, setTagsInput] = useState("");
  const [mistakeTag, setMistakeTag] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<JournalEntryList>("journal-studio/entries");
      setList(data);
    } catch {
      setList(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const createEntry = useCallback(async () => {
    if (!thesis.trim()) {
      toast.error("Thesis is required.");
      return;
    }
    setSaving(true);
    try {
      const tags = tagsInput
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean);
      await hivePostJson("journal-studio/entries", {
        thesis: thesis.trim(),
        lesson: lesson.trim(),
        outcome,
        tags,
        mistake_tag: mistakeTag.trim() || null,
      });
      toast.success("Journal entry saved.");
      setThesis("");
      setLesson("");
      setOutcome("unknown");
      setTagsInput("");
      setMistakeTag("");
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }, [lesson, load, mistakeTag, outcome, tagsInput, thesis]);

  const quickPatchLesson = useCallback(
    async (entryId: string, nextLesson: string) => {
      try {
        await hivePatchJson(`journal-studio/entries/${encodeURIComponent(entryId)}`, {
          lesson: nextLesson,
        });
        toast.success("Lesson updated.");
        await load();
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Update failed");
      }
    },
    [load],
  );

  if (loading) {
    return (
      <div data-testid="journal-studio-entries-panel">
        <V4Card className="flex items-center gap-2 p-4 text-sm text-white/60">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading journal entries…
        </V4Card>
      </div>
    );
  }

  const fields = list?.enabled_fields ?? ["thesis", "lesson", "outcome", "tags", "mistake_tag"];

  return (
    <div className="space-y-4" data-testid="journal-studio-entries-panel">
      <V4Card id="journal-studio-entries" className="border-amber-500/25">
        <V4CardHeader
          leadingIcon={NotebookPen}
          title="Trade entries"
          description="Thesis, outcome, tags, and lesson — manual rows or imported from paper fills."
          actions={<HiveRefreshButton onClick={() => void load()} aria-label="Refresh journal entries" />}
        />
        <p className="mt-3 text-sm text-white/70">{list?.operator_hint ?? "No entries loaded."}</p>

        <div className="mt-4 grid gap-3">
          {fieldEnabled(fields, "thesis") ? (
            <label className="grid gap-1 text-sm">
              <span className="text-white/70">Thesis</span>
              <textarea
                className="min-h-[72px] rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-white"
                value={thesis}
                onChange={(e) => setThesis(e.target.value)}
                data-testid="journal-entry-thesis"
              />
            </label>
          ) : null}
          {fieldEnabled(fields, "outcome") ? (
            <label className="grid gap-1 text-sm">
              <span className="text-white/70">Outcome</span>
              <select
                className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-white"
                value={outcome}
                onChange={(e) => setOutcome(e.target.value as EntryOutcome)}
                data-testid="journal-entry-outcome"
              >
                {OUTCOME_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          {fieldEnabled(fields, "lesson") ? (
            <label className="grid gap-1 text-sm">
              <span className="text-white/70">Lesson learned</span>
              <textarea
                className="min-h-[72px] rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-white"
                value={lesson}
                onChange={(e) => setLesson(e.target.value)}
                data-testid="journal-entry-lesson"
              />
            </label>
          ) : null}
          {fieldEnabled(fields, "tags") ? (
            <label className="grid gap-1 text-sm">
              <span className="text-white/70">Tags (comma-separated)</span>
              <input
                className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-white"
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                data-testid="journal-entry-tags"
              />
            </label>
          ) : null}
          {fieldEnabled(fields, "mistake_tag") ? (
            <label className="grid gap-1 text-sm">
              <span className="text-white/70">Mistake tag</span>
              <input
                className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-white"
                value={mistakeTag}
                onChange={(e) => setMistakeTag(e.target.value)}
                data-testid="journal-entry-mistake-tag"
              />
            </label>
          ) : null}
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-amber-500/20 px-4 py-2 text-sm font-medium text-amber-200 hover:bg-amber-500/30"
            onClick={() => void createEntry()}
            disabled={saving}
            data-testid="journal-entry-save"
          >
            {saving ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Plus className="size-4" aria-hidden />}
            Save entry
          </button>
        </div>
      </V4Card>

      <V4Card>
        <V4CardHeader leadingIcon={NotebookPen} title="Saved entries" description={`${list?.entry_count ?? 0} rows`} />
        {(list?.items.length ?? 0) === 0 ? (
          <p className="mt-4 text-sm text-white/60">No entries yet.</p>
        ) : (
          <ul className="mt-4 space-y-3">
            {list?.items.map((entry) => (
              <li
                key={entry.id}
                className="rounded-lg border border-white/10 bg-white/[0.02] p-3"
                data-testid={`journal-entry-row-${entry.id}`}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <V4Badge tone={entry.source === "paper_fill" ? "info" : "purple"}>
                    {entry.source === "paper_fill" ? "Paper import" : "Manual"}
                  </V4Badge>
                  {entry.symbol ? <V4Badge tone="info">{entry.symbol}</V4Badge> : null}
                  <V4Badge tone="warn">{entry.outcome}</V4Badge>
                  <span className="font-medium text-white">{entry.thesis || "Untitled entry"}</span>
                </div>
                {entry.lesson ? <p className="mt-2 text-sm text-white/70">{entry.lesson}</p> : null}
                {entry.tags.length > 0 ? (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {entry.tags.map((tag) => (
                      <V4Badge key={`${entry.id}-${tag}`} tone="purple">
                        {tag}
                      </V4Badge>
                    ))}
                  </div>
                ) : null}
                {!entry.lesson ? (
                  <button
                    type="button"
                    className="mt-2 text-xs text-cyan-300 hover:underline"
                    onClick={() => void quickPatchLesson(entry.id, "Add lesson after review.")}
                  >
                    Add placeholder lesson
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </V4Card>
    </div>
  );
}
