"use client";

import { Loader2Icon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { usePlatform } from "@/components/hive/platform-context";
import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge, V4Card, V4CardHeader, V4FormField, V4FormStack } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePutJson } from "@/lib/api";

interface RecallSettings {
  recall_mode: "full" | "selective";
  token_budget_chars: number;
  feature_enabled: boolean;
  max_prompt_chars: number;
  selective_max_chars: number;
}

interface RecallPreview {
  recall_mode: string;
  characters: number;
  char_budget: number;
  hive_mind_prompt_block: string;
}

const MODE_OPTIONS = [
  { value: "selective", label: "Selective — graph-neighbour RAG + token cap" },
  { value: "full", label: "Full — wider vector + graph context" },
] as const;

/** Knowledge hub — tenant recall mode + live preview vs token budget. */
export function SelectiveRecallPanel(): JSX.Element | null {
  const { hasFeature } = usePlatform();
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [settings, setSettings] = useState<RecallSettings | null>(null);
  const [previewQuery, setPreviewQuery] = useState("project priorities and stalled tasks");
  const [preview, setPreview] = useState<RecallPreview | null>(null);

  const load = useCallback(async () => {
    try {
      const body = await hiveGet<RecallSettings>("hive-mind/recall-settings");
      setSettings(body);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Recall settings unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const save = useCallback(
    async (patch: Partial<RecallSettings>) => {
      if (!settings) return;
      setBusy(true);
      try {
        const body = await hivePutJson<RecallSettings>("hive-mind/recall-settings", {
          recall_mode: patch.recall_mode ?? settings.recall_mode,
          token_budget_chars: patch.token_budget_chars ?? settings.token_budget_chars,
        });
        setSettings(body);
        toast.success("Recall settings saved.");
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Save failed.");
      } finally {
        setBusy(false);
      }
    },
    [settings],
  );

  const runPreview = useCallback(async () => {
    setBusy(true);
    try {
      const body = await hiveGet<RecallPreview>(
        `hive-mind/recall-preview?q=${encodeURIComponent(previewQuery.trim())}`,
      );
      setPreview(body);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Preview failed.");
    } finally {
      setBusy(false);
    }
  }, [previewQuery]);

  if (!hasFeature("selective_recall")) {
    return null;
  }

  return (
    <V4Card className="v4-card-interactive border-(--qs-magenta)/25">
      <V4CardHeader
        title="Selective recall"
        description="Graph-neighbour RAG with similarity pruning — injects less tokens into supervisor prompts."
      />

      {loading ? (
        <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading recall settings…
        </p>
      ) : null}

      {settings ? (
        <V4FormStack>
          <V4FormField label="Recall mode">
            <QsSelect
              value={settings.recall_mode}
              options={MODE_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
              onValueChange={(value) => void save({ recall_mode: value as RecallSettings["recall_mode"] })}
              disabled={busy}
            />
          </V4FormField>

          <V4FormField
            label="Token budget override (chars, 0 = default)"
            footer={
              <>
                <V4Badge tone="info">cap {settings.selective_max_chars} chars</V4Badge>
                <V4Badge tone="warn">max {settings.max_prompt_chars} hard</V4Badge>
              </>
            }
          >
            <input
              type="number"
              min={0}
              max={settings.max_prompt_chars}
              value={settings.token_budget_chars}
              onChange={(e) => void save({ token_budget_chars: Number(e.target.value) })}
              className="qs-input w-full max-w-xs"
              disabled={busy}
            />
          </V4FormField>

          <V4FormField label="Preview query">
            <div className="flex flex-wrap gap-2">
              <input
                type="text"
                value={previewQuery}
                onChange={(e) => setPreviewQuery(e.target.value)}
                className="qs-input min-w-[220px] flex-1"
                disabled={busy}
              />
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" disabled={busy} onClick={() => void runPreview()}>
                Preview recall
              </button>
            </div>
          </V4FormField>

          {preview ? (
            <div className="space-y-2 rounded-xl border border-white/10 bg-black/25 p-3">
              <div className="flex flex-wrap gap-2">
                <V4Badge tone="ok">{preview.characters} chars</V4Badge>
                <V4Badge tone="info">budget {preview.char_budget}</V4Badge>
                <V4Badge tone="warn">{preview.recall_mode}</V4Badge>
              </div>
              <pre className="max-h-48 overflow-auto whitespace-pre-wrap font-mono text-xs text-(--qs-text-2)">
                {preview.hive_mind_prompt_block || "(empty recall block)"}
              </pre>
            </div>
          ) : null}
        </V4FormStack>
      ) : null}
    </V4Card>
  );
}
