"use client";

import { ChevronDown, ChevronUp, Link2, Loader2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

interface BatchSnapshot {
  enabled: boolean;
  max_urls: number;
  excerpt_chars: number;
  knowledge_href: string;
  tasks_href: string;
}

interface BatchSubmitResponse {
  ok: boolean;
  task_id: string;
  title: string;
  href: string;
  url_count: number;
  ok_count: number;
  partial_count: number;
  error_count: number;
  gardener_triggered: boolean;
  message: string;
}

interface VideoUrlBatchWizardPanelProps {
  onSubmitted?: () => void;
}

export function VideoUrlBatchWizardPanel({
  onSubmitted,
}: VideoUrlBatchWizardPanelProps): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<BatchSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [urlsText, setUrlsText] = useState("");
  const [briefTitle, setBriefTitle] = useState("");
  const [wikiCapture, setWikiCapture] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [lastResult, setLastResult] = useState<BatchSubmitResponse | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<BatchSnapshot>("solo-operator/video-url-batch");
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
    if (!urlsText.trim()) {
      toast.error("Paste at least one URL");
      return;
    }
    setSubmitting(true);
    try {
      const data = await hivePostJson<BatchSubmitResponse>("solo-operator/video-url-batch/submit", {
        urls_text: urlsText,
        title: briefTitle.trim() || null,
        wiki_capture: wikiCapture,
        trigger_gardener: wikiCapture,
      });
      setLastResult(data);
      toast.success(data.message || "Batch digest saved");
      onSubmitted?.();
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Submit failed";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  }, [briefTitle, onSubmitted, urlsText, wikiCapture]);

  if (loading) {
    return (
      <V4Card className="mb-4 flex items-center gap-2 p-4 text-sm text-white/60">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Loading video batch wizard…
      </V4Card>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  return (
    <V4Card className="mb-4 max-lg:mb-3 border-cyan-500/25" id="video-url-batch-wizard">
      <V4CardHeader
        kicker="NP8 · Video intel batch"
        title="Video URL batch digest"
        description={`Paste 1–${snapshot.max_urls} URLs — oEmbed title + transcript/web excerpt → Kanban triage + wiki raw.`}
        actions={
          <div className="flex items-center gap-2">
            <V4Badge tone="info">max {snapshot.max_urls}</V4Badge>
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
            YouTube uses transcript bee (no Ask-YouTube). Other URLs use Research Bee fetch.{" "}
            <Link href={snapshot.knowledge_href} className="text-[#00FFFF] hover:underline">
              Wiki raw tier
            </Link>
          </p>
          <label className="block text-sm">
            <span className="text-white/60">Digest title (optional)</span>
            <input
              className="qs-input mt-1 w-full"
              value={briefTitle}
              onChange={(e) => setBriefTitle(e.target.value)}
              placeholder="Jun 2026 agent video review"
            />
          </label>
          <label className="block text-sm">
            <span className="text-white/60">URLs (one per line or comma-separated)</span>
            <textarea
              className="qs-input mt-1 min-h-[120px] w-full font-mono text-sm"
              value={urlsText}
              onChange={(e) => setUrlsText(e.target.value)}
              placeholder={"https://www.youtube.com/watch?v=…\nhttps://x.com/…"}
            />
          </label>
          <label className="flex items-center gap-2 text-sm text-white/80">
            <input type="checkbox" checked={wikiCapture} onChange={(e) => setWikiCapture(e.target.checked)} />
            Persist to wiki raw tier + run Gardener
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="qs-btn qs-btn--primary"
              disabled={submitting}
              onClick={() => void submit()}
            >
              {submitting ? <Loader2 className="size-4 animate-spin" /> : <Link2 className="size-4" />}
              Build digest
            </button>
          </div>
          {lastResult ? (
            <p className="text-sm text-[#00FF88]">
              {lastResult.url_count} URLs — {lastResult.ok_count} OK · {lastResult.partial_count} partial ·{" "}
              {lastResult.error_count} failed —{" "}
              <Link href={lastResult.href} className="underline">
                open task
              </Link>
              {lastResult.gardener_triggered ? " · Gardener triggered" : null}
            </p>
          ) : null}
        </div>
      ) : (
        <p className="px-4 pb-4 text-sm text-white/60">
          Batch review workflow — paste YouTube/X/article URLs for a single markdown intel brief
        </p>
      )}
    </V4Card>
  );
}
