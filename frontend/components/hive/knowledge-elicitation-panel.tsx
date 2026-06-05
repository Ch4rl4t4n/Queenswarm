"use client";

import { Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

interface ElicitationPrompt {
  id: string;
  kind: string;
  title: string;
  question: string;
  empty: boolean;
  current_preview: string;
}

interface ElicitationSnapshot {
  enabled: boolean;
  gap_count: number;
  filled_count: number;
  prompts: ElicitationPrompt[];
}

export function KnowledgeElicitationPanel(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<ElicitationSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [savingKind, setSavingKind] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<ElicitationSnapshot>("memory/wiki-layer/elicitation");
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

  const save = useCallback(
    async (kind: string) => {
      const answer = answers[kind]?.trim();
      if (!answer || answer.length < 8) {
        toast.error("Answer must be at least 8 characters.");
        return;
      }
      setSavingKind(kind);
      try {
        const data = await hivePostJson<ElicitationSnapshot>("memory/wiki-layer/elicitation", {
          kind,
          answer,
        });
        setSnapshot(data);
        toast.success("Saved to Brain Pack");
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Save failed");
      } finally {
        setSavingKind(null);
      }
    },
    [answers],
  );

  if (loading && !snapshot) {
    return (
      <V4Card className="mb-4">
        <div className="flex items-center gap-2 p-4 text-sm text-(--qs-muted)">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading elicitation prompts…
        </div>
      </V4Card>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  return (
    <V4Card className="mb-4 border-cyan/25" id="knowledge-elicitation">
      <V4CardHeader
        kicker="Knowledge elicitation"
        title="Brain Pack gaps"
        description="Answer prompts to strengthen curated memory — no LLM auto-write."
        actions={<HiveRefreshButton busy={loading} onClick={() => void load()} />}
      />
      <p className="mb-3 text-xs text-(--qs-text-2)">
        {snapshot.filled_count} filled · {snapshot.gap_count} gap(s)
      </p>
      <ul className="space-y-3">
        {snapshot.prompts.map((prompt) => (
          <li key={prompt.id} className="rounded-lg border border-(--qs-border) bg-(--qs-surface) p-3">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className="font-medium text-(--qs-text)">{prompt.title}</span>
              <V4Badge tone={prompt.empty ? "warn" : "ok"}>{prompt.empty ? "empty" : "filled"}</V4Badge>
            </div>
            <p className="mb-2 text-xs text-(--qs-text-2)">{prompt.question}</p>
            {prompt.empty ? (
              <>
                <textarea
                  className="qs-input mb-2 min-h-[72px] w-full text-sm"
                  value={answers[prompt.kind] ?? ""}
                  onChange={(e) => setAnswers((prev) => ({ ...prev, [prompt.kind]: e.target.value }))}
                  placeholder="Your answer…"
                />
                <button
                  type="button"
                  className="qs-btn qs-btn--primary qs-btn--sm"
                  disabled={savingKind === prompt.kind}
                  onClick={() => void save(prompt.kind)}
                >
                  {savingKind === prompt.kind ? "Saving…" : "Save to Brain Pack"}
                </button>
              </>
            ) : (
              <p className="text-xs text-(--qs-muted)">{prompt.current_preview}</p>
            )}
          </li>
        ))}
      </ul>
    </V4Card>
  );
}
