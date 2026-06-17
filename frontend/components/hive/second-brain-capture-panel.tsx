"use client";

import { LightbulbIcon, Loader2Icon, PlusIcon } from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { V4Card, V4CardHeader, V4FormField, V4FormStack } from "@/components/ui/v4";
import { HiveApiError, hivePostJson } from "@/lib/api";

interface CaptureResponse {
  id: string;
  markdown: string;
  topic_tags: string[];
}

export interface SecondBrainCapturePanelProps {
  onCaptured?: () => void;
}

/** Quick capture — IDEA / CONNECTS TO / MIGHT USE FOR / Key Tension. */
export function SecondBrainCapturePanel({ onCaptured }: SecondBrainCapturePanelProps): JSX.Element {
  const [busy, setBusy] = useState(false);
  const [idea, setIdea] = useState("");
  const [connectsTo, setConnectsTo] = useState("");
  const [mightUseFor, setMightUseFor] = useState("");
  const [keyTension, setKeyTension] = useState("");

  const submit = useCallback(async () => {
    const trimmed = idea.trim();
    if (trimmed.length < 3) {
      toast.error("IDEA needs at least 3 characters.");
      return;
    }
    setBusy(true);
    try {
      const connects = connectsTo
        .split(/[\n,]/)
        .map((item) => item.trim())
        .filter(Boolean);
      await hivePostJson<CaptureResponse>("memory/wiki-layer/capture", {
        idea: trimmed,
        connects_to: connects,
        might_use_for: mightUseFor.trim(),
        key_tension: keyTension.trim(),
      });
      toast.success("Capture saved — approve below for Obsidian wikilinks.");
      setIdea("");
      setConnectsTo("");
      setMightUseFor("");
      setKeyTension("");
      onCaptured?.();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Capture failed.");
    } finally {
      setBusy(false);
    }
  }, [connectsTo, idea, keyTension, mightUseFor, onCaptured]);

  return (
    <V4Card>
      <V4CardHeader
        title="Quick capture"
        description="Second-brain convention — links compound when Gardener builds Maps of Content + Connection intelligence."
        actions={
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm inline-flex items-center gap-1"
            disabled={busy}
            onClick={() => void submit()}
          >
            {busy ? <Loader2Icon className="size-3.5 animate-spin" aria-hidden /> : <PlusIcon className="size-3.5" aria-hidden />}
            Save capture
          </button>
        }
      />
      <V4FormStack>
        <V4FormField label="IDEA" footer={<span className="inline-flex items-center gap-1"><LightbulbIcon className="size-3" aria-hidden />One sentence core insight</span>}>
          <textarea
            className="qs-input min-h-[72px] w-full font-sans text-sm"
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="e.g. Newsletter loop compounds when each issue links back to SEO pipeline"
            disabled={busy}
          />
        </V4FormField>
        <V4FormField label="CONNECTS TO" footer="Comma or newline separated — wikilink targets or topics">
          <input
            className="qs-input w-full text-sm"
            value={connectsTo}
            onChange={(e) => setConnectsTo(e.target.value)}
            placeholder="seo-pipeline, factory-queue"
            disabled={busy}
          />
        </V4FormField>
        <V4FormField label="MIGHT USE FOR">
          <input
            className="qs-input w-full text-sm"
            value={mightUseFor}
            onChange={(e) => setMightUseFor(e.target.value)}
            placeholder="Skill Factory launch, Gumroad pack"
            disabled={busy}
          />
        </V4FormField>
        <V4FormField label="Key Tension">
          <input
            className="qs-input w-full text-sm"
            value={keyTension}
            onChange={(e) => setKeyTension(e.target.value)}
            placeholder="Speed vs depth, automation vs voice"
            disabled={busy}
          />
        </V4FormField>
      </V4FormStack>
    </V4Card>
  );
}
