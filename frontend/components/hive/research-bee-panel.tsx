"use client";

import { BookOpen, Download, Loader2 } from "lucide-react";
import { memo, useCallback, useState } from "react";

import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hivePostJson } from "@/lib/api";
import { downloadResearchBriefExportBundle, type ResearchBriefExportResponse } from "@/lib/research-brief-export-utils";
import { parseResearchProjectUrls } from "@/lib/research-project-urls";
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
  const [exportBusy, setExportBusy] = useState(false);
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

  const exportB2bBundle = useCallback(async () => {
    setExportBusy(true);
    onError(null);
    try {
      const body = {
        source_url: url.trim() || null,
        content_text: paste.trim() || null,
        title_hint: titleHint.trim() || null,
        persist,
        trigger_gardener: triggerGardener,
      };
      const bundle = await hivePostJson<ResearchBriefExportResponse>("research-bee/brief/export", body);
      await downloadResearchBriefExportBundle(bundle);
    } catch (err) {
      onError(err instanceof HiveApiError ? err.message : "B2B export failed.");
    } finally {
      setExportBusy(false);
    }
  }, [url, paste, titleHint, persist, triggerGardener, onError]);

  return (
    <div className="space-y-4">
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

      <div className="flex flex-wrap gap-2">
        <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" disabled={loading} onClick={() => void submit()}>
          {loading ? <Loader2 className="size-4 animate-spin" aria-hidden /> : null}
          Ingest &amp; generate brief
        </button>
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm"
          disabled={exportBusy || loading || (!url.trim() && !paste.trim())}
          onClick={() => void exportB2bBundle()}
        >
          {exportBusy ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Download className="size-4" aria-hidden />}
          Export B2B pack
        </button>
      </div>

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

    <V4Card className="border-pollen/25" data-testid="research-bee-project">
      <V4CardHeader
        leadingIcon={BookOpen}
        leadingIconTone="cyan"
        title="Research project"
        description="Batch public URLs → one merged Hive Mind brief (POS-H3). No raw LLM dump."
      />
      <ResearchProjectForm onError={onError} />
    </V4Card>
    </div>
  );
}

interface ResearchProjectSource {
  url: string;
  ok: boolean;
  title: string;
  error: string | null;
}

interface ResearchProjectBrief {
  enabled: boolean;
  project_title: string;
  source_count: number;
  sources: ResearchProjectSource[];
  summary: string;
  key_points: string[];
  topic_tags: string[];
  persisted: boolean;
  knowledge_item_id: string | null;
}

interface ResearchProjectFormProps {
  onError: (message: string | null) => void;
}

function parseProjectUrls(raw: string): string[] {
  return parseResearchProjectUrls(raw, 8);
}

function countRawProjectUrlLines(raw: string): number {
  return raw.split("\n").filter((line) => line.trim().length > 0).length;
}

function ResearchProjectForm({ onError }: ResearchProjectFormProps) {
  const [urlsText, setUrlsText] = useState("");
  const [projectTitle, setProjectTitle] = useState("");
  const [persistProject, setPersistProject] = useState(true);
  const [loading, setLoading] = useState(false);
  const [project, setProject] = useState<ResearchProjectBrief | null>(null);

  const submitProject = useCallback(async () => {
    const source_urls = parseProjectUrls(urlsText);
    if (source_urls.length === 0) {
      onError("Add at least one public https URL (one per line).");
      return;
    }
    setLoading(true);
    onError(null);
    try {
      const data = await hivePostJson<ResearchProjectBrief>("research-bee/project", {
        source_urls,
        project_title: projectTitle.trim() || null,
        persist: persistProject,
      });
      setProject(data);
    } catch (err) {
      onError(err instanceof HiveApiError ? err.message : "Research project failed.");
    } finally {
      setLoading(false);
    }
  }, [urlsText, projectTitle, persistProject, onError]);

  const urlCount = parseProjectUrls(urlsText).length;
  const rawLineCount = countRawProjectUrlLines(urlsText);
  const dedupedCount = rawLineCount - urlCount;

  return (
    <div className="space-y-3 p-4 pt-0">
      <p className="text-xs text-(--qs-text-3)">
        Paste up to 8 article or report URLs — merged brief for supervisor sessions and Wiki capture.
      </p>
      <label className="block space-y-1 text-xs">
        <span className="text-(--qs-text-3)">URLs (one per line)</span>
        <textarea
          value={urlsText}
          onChange={(e) => setUrlsText(e.target.value)}
          rows={5}
          placeholder={"https://example.com/report-a\nhttps://example.com/report-b"}
          className="qs-input w-full font-mono text-[11px]"
          disabled={loading}
          data-testid="research-project-urls"
        />
      </label>
      <div className="grid gap-2 sm:grid-cols-2">
        <label className="space-y-1 text-xs">
          <span className="text-(--qs-text-3)">Project title (optional)</span>
          <input
            value={projectTitle}
            onChange={(e) => setProjectTitle(e.target.value)}
            placeholder="Q2 competitor scan"
            className="qs-input w-full"
            disabled={loading}
          />
        </label>
        <p className="flex items-end text-xs text-(--qs-muted)">
          {urlCount}/8 unique URLs
          {dedupedCount > 0 ? (
            <span className="ml-2 text-(--qs-cyan)" data-testid="research-project-dedupe-hint">
              ({rawLineCount} lines → {urlCount} after dedupe)
            </span>
          ) : null}
        </p>
      </div>
      <label className="flex items-center gap-2 text-xs text-(--qs-text-2)">
        <input
          type="checkbox"
          checked={persistProject}
          onChange={(e) => setPersistProject(e.target.checked)}
        />
        Persist merged brief to HiveMind
      </label>
      <button
        type="button"
        className="qs-btn qs-btn--primary qs-btn--sm"
        disabled={loading || urlCount === 0}
        data-testid="research-project-submit"
        onClick={() => void submitProject()}
      >
        {loading ? <Loader2 className="size-4 animate-spin" aria-hidden /> : null}
        Run research project
      </button>
      {project ? (
        <article className="space-y-2 rounded-lg border border-pollen/20 bg-black/25 p-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="font-medium text-(--qs-text)">{project.project_title}</h4>
            <V4Badge tone="info">{project.source_count} sources</V4Badge>
            {project.persisted ? <V4Badge tone="ok">Saved</V4Badge> : null}
          </div>
          <p className="text-xs text-(--qs-text-2)">{project.summary}</p>
          {project.key_points.length > 0 ? (
            <ul className="list-disc space-y-1 pl-4 text-xs text-(--qs-text-3)">
              {project.key_points.slice(0, 5).map((point) => (
                <li key={point.slice(0, 40)}>{point}</li>
              ))}
            </ul>
          ) : null}
          <ul className="space-y-1 text-[10px] text-(--qs-muted)">
            {project.sources.map((row) => (
              <li key={row.url} className={row.ok ? "text-[#00FF88]" : "text-[#FF3366]"}>
                {row.ok ? "OK" : "FAIL"} · {row.title || row.url}
              </li>
            ))}
          </ul>
        </article>
      ) : null}
    </div>
  );
}

export const ResearchBeePanel = memo(ResearchBeePanelInner);
