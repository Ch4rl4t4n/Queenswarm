"use client";

import Link from "next/link";
import { Loader2, Sparkles, Wand2 } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HivePanelSectionSkeleton } from "@/components/hive/hive-panel-section-skeleton";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { COCKPIT_POLL_BOARD_MS } from "@/lib/cockpit-poll-profile";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";

type PublishChannel = "instagram" | "facebook" | "twitter" | "tiktok" | "newsletter";

interface FacelessPipelineItem {
  deliverable_id: string;
  title: string;
  channel: string;
  status: string;
  scheduled_at: string | null;
  body_preview: string;
  href: string;
}

interface FacelessPipelineSnapshot {
  enabled: boolean;
  draft_count: number;
  scheduled_count: number;
  recent_items: FacelessPipelineItem[];
  links: Record<string, string>;
  operator_hint: string;
}

const CHANNELS: PublishChannel[] = ["instagram", "tiktok", "facebook", "twitter", "newsletter"];

function FacelessStudioPanelInner(): JSX.Element {
  const [snapshot, setSnapshot] = useState<FacelessPipelineSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [idea, setIdea] = useState("");
  const [channel, setChannel] = useState<PublishChannel>("instagram");
  const [createTask, setCreateTask] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<FacelessPipelineSnapshot>("operator/faceless-pipeline");
      setSnapshot(data);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Faceless pipeline unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  useIntervalWhenVisible(() => void reload(), COCKPIT_POLL_BOARD_MS);

  async function runDraft() {
    const trimmed = idea.trim();
    if (trimmed.length < 8) {
      toast.error("Idea must be at least 8 characters");
      return;
    }
    setBusy(true);
    try {
      const res = await hivePostJson<{
        ok: boolean;
        title?: string;
        href?: string;
        queue_status?: string;
      }>("operator/faceless-pipeline/draft", {
        idea: trimmed,
        channel,
        create_intake_task: createTask,
      });
      toast.success(res.title ? `${res.title} → ${res.queue_status ?? "queue"}` : "Draft created");
      setIdea("");
      await reload();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Draft failed");
    } finally {
      setBusy(false);
    }
  }

  if (loading && !snapshot) {
    return <HivePanelSectionSkeleton label="Loading Faceless Studio" minHeightClass="min-h-[14rem]" />;
  }

  if (!snapshot?.enabled) {
    return (
      <V4Card>
        <V4CardHeader kicker="Studio" title="Faceless pipeline" description="Disabled on this deployment." />
      </V4Card>
    );
  }

  return (
    <div className="flex flex-col gap-3" data-testid="faceless-studio-panel">
      <V4Card>
        <V4CardHeader
          kicker="Faceless Studio"
          title="Idea → draft pack"
          description={snapshot.operator_hint}
          actions={<HiveRefreshButton busy={loading} onClick={() => void reload()} />}
        />
        <div className="space-y-3 px-4 pb-4">
          <label className="block text-xs font-medium text-(--qs-text-3)" htmlFor="faceless-idea">
            Hook / idea
          </label>
          <textarea
            id="faceless-idea"
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            rows={3}
            placeholder="e.g. How I automate content with agent swarms in 15 minutes/day"
            className="w-full rounded-xl border border-(--qs-border)/50 bg-black/30 px-3 py-2 text-sm text-(--qs-text-1)"
          />
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-xs text-(--qs-text-3)" htmlFor="faceless-channel">
              Channel
            </label>
            <select
              id="faceless-channel"
              value={channel}
              onChange={(e) => setChannel(e.target.value as PublishChannel)}
              className="rounded-lg border border-(--qs-border)/50 bg-black/30 px-2 py-1.5 text-sm"
            >
              {CHANNELS.map((row) => (
                <option key={row} value={row}>
                  {row}
                </option>
              ))}
            </select>
            <label className="flex items-center gap-2 text-xs text-(--qs-text-2)">
              <input
                type="checkbox"
                checked={createTask}
                onChange={(e) => setCreateTask(e.target.checked)}
              />
              Also create Kanban task
            </label>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm gap-1"
              disabled={busy}
              onClick={() => void runDraft()}
            >
              {busy ? <Loader2 className="size-3.5 animate-spin" aria-hidden /> : <Wand2 className="size-3.5" aria-hidden />}
              Generate draft pack
            </button>
            <Link href={snapshot.links.agents ?? "/agents?preset=faceless-video#sessions"} className="qs-btn qs-btn--ghost qs-btn--sm gap-1">
              <Sparkles className="size-3.5" aria-hidden />
              Agent session
            </Link>
          </div>
        </div>
      </V4Card>

      <V4Card>
        <V4CardHeader
          kicker="Recent"
          title={`${snapshot.draft_count} drafts · ${snapshot.scheduled_count} scheduled`}
          description="Approve in Publish Queue → simulate in Social publish."
        />
        <ul className="space-y-2 px-4 pb-4">
          {snapshot.recent_items.map((item) => (
            <li key={item.deliverable_id}>
              <Link
                href={item.href}
                className="block rounded-xl border border-(--qs-border)/40 px-3 py-2 text-sm hover:border-cyan/40"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium">{item.title}</span>
                  <span className="text-[11px] uppercase text-(--qs-text-3)">{item.status}</span>
                </div>
                <p className="text-xs text-(--qs-text-3)">
                  {item.channel}
                  {item.scheduled_at ? ` · ${new Date(item.scheduled_at).toLocaleString()}` : ""}
                </p>
              </Link>
            </li>
          ))}
          {snapshot.recent_items.length === 0 ? (
            <li className="text-sm text-(--qs-text-3)">No faceless drafts yet — paste a hook above.</li>
          ) : null}
        </ul>
      </V4Card>
    </div>
  );
}

export const FacelessStudioPanel = memo(FacelessStudioPanelInner);
