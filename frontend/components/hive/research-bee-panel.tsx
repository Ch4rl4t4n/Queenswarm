"use client";

import { BookOpen, Loader2 } from "lucide-react";
import { memo, useCallback, useState } from "react";

import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hivePostJson } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ResearchBrief {
  enabled: boolean;
  title: string;
  summary: string;
  key_points: string[];
  notable_quotes: string[];
  topic_tags: string[];
  word_count: number;
  persisted: boolean;
  knowledge_item_id: string | null;
  source_label: string;
  ingest_route?: string;
  video_id?: string | null;
  transcript_language?: string | null;
  gardener_triggered?: boolean;
}

export interface ResearchBeePanelProps {
  onError: (message: string | null) => void;
}

function ResearchBeePanelInner({ onError }: ResearchBeePanelProps) {
  const [url, setUrl] = useState("");
  const [paste, setPaste] = useState("");
  const [titleHint, setTitleHint] = useState("");
  const [persist, setPersist] = useState(true);
  const [triggerGardener, setTriggerGardener] = useState(true);
  const [loading, setLoading] = useState(false);
  const [brief, setBrief] = useState<ResearchBrief | null>(null);

  const submit = useCallback(async () => {
    setLoading(true);
    onError(null);
    try {
      const body = {
        source_url: url.trim() || null,
        content_text: paste.trim() || null,
        title_hint: titleHint.trim() || null,
        persist,
        trigger_gardener: triggerGardener,
      };
      const data = await hivePostJson<ResearchBrief>("research-bee/brief", body);
      setBrief(data);
    } catch (err) {
      onError(err instanceof HiveApiError ? err.message : "Research brief failed.");
    } finally {
      setLoading(false);
    }
  }, [url, paste, titleHint, persist, triggerGardener, onError]);

  return (
    <V4Card className="border-(--qs-cyan)/25">
      <V4CardHeader
        leadingIcon={BookOpen}
        leadingIconTone="cyan"
        title="Ingest URL / Research Bee"
        description="YouTube transcript, public web page, or pasted text → structured brief. Routes through Ingest Router — never raw dump."
        hint={sectionHintNode("knowledgeIngestRouter")}
      />

      <div className="space-y-3 p-4 pt-0">
      <p className="text-xs text-(--qs-text-3)">
        Drop a YouTube link for auto-transcript, or any public https URL. Persist sends to HiveMind raw zone; Gardener compiles into Wiki Layer.
      </p>

      <div className="grid gap-2 sm:grid-cols-2">
        <label className="space-y-1 text-xs">
          <span className="inline-flex items-center gap-1 text-(--qs-text-3)">
            Public URL
            {sectionHintNode("knowledgeYouTubeIngest")}
          </span>
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://youtube.com/watch?v=… or article URL"
            className="qs-input w-full"
            disabled={loading}
          />
        </label>
        <label className="space-y-1 text-xs">
          <span className="text-(--qs-text-3)">Title hint (optional)</span>
          <input
            value={titleHint}
            onChange={(e) => setTitleHint(e.target.value)}
            placeholder="Brief title"
            className="qs-input w-full"
            disabled={loading}
          />
        </label>
      </div>

      <label className="block space-y-1 text-xs">
        <span className="text-(--qs-text-3)">Or paste PDF/text extract</span>
        <textarea
          value={paste}
          onChange={(e) => setPaste(e.target.value)}
          rows={4}
          placeholder="Paste extracted text from PDF or notes…"
          className="qs-input w-full font-mono text-[11px]"
          disabled={loading}
        />
      </label>

      <label className="flex items-center gap-2 text-xs text-(--qs-text-2)">
        <input type="checkbox" checked={persist} onChange={(e) => setPersist(e.target.checked)} />
        Persist verified brief to HiveMind (raw zone)
      </label>

      <label className="flex items-center gap-2 text-xs text-(--qs-text-2)">
        <input type="checkbox" checked={triggerGardener} onChange={(e) => setTriggerGardener(e.target.checked)} disabled={!persist} />
        Run Wiki Gardener after save (updates forager-insights wiki)
      </label>

      <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" disabled={loading} onClick={() => void submit()}>
        {loading ? <Loader2 className="size-4 animate-spin" aria-hidden /> : null}
        Ingest &amp; generate brief
      </button>

      {brief ? (
        <article className="space-y-2 rounded-lg border border-white/10 bg-black/25 p-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="font-medium text-(--qs-text)">{brief.title}</h4>
            {brief.persisted ? <V4Badge tone="ok">Saved</V4Badge> : null}
            {brief.gardener_triggered ? <V4Badge tone="gold">Gardener</V4Badge> : null}
            {brief.ingest_route === "youtube" ? <V4Badge tone="purple">YouTube</V4Badge> : null}
            <span className="font-mono text-[10px] text-(--qs-text-3)">{brief.word_count} words</span>
          </div>
          <p className="text-xs text-(--qs-text-2)">{brief.summary}</p>
          {brief.key_points.length > 0 ? (
            <ul className="list-disc space-y-1 pl-4 text-xs text-(--qs-text-3)">
              {brief.key_points.slice(0, 5).map((point) => (
                <li key={point.slice(0, 40)}>{point}</li>
              ))}
            </ul>
          ) : null}
          {brief.topic_tags.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {brief.topic_tags.map((tag) => (
                <V4Badge key={tag} tone="info">
                  {tag}
                </V4Badge>
              ))}
            </div>
          ) : null}
          <p className={cn("truncate text-[10px] text-(--qs-text-3)")}>{brief.source_label}</p>
          {brief.transcript_language ? (
            <p className="text-[10px] text-(--qs-text-3)">Transcript: {brief.transcript_language}</p>
          ) : null}
        </article>
      ) : null}
      </div>
    </V4Card>
  );
}

export const ResearchBeePanel = memo(ResearchBeePanelInner);
