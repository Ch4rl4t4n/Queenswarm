"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { Loader2, Play, Sunrise } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { InfoHint } from "@/components/hive/info-hint";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { cn } from "@/lib/utils";

interface PipelineStep {
  id: string;
  label: string;
  scheduled_at: string;
  status: "ready" | "pending" | "running" | "done" | "skipped" | "blocked";
  detail: string;
  routine_name: string | null;
  last_session_status: string | null;
}

interface MorningPublishPipelineSnapshot {
  enabled: boolean;
  generated_at: string;
  life_os_bound: boolean;
  content_routine_bound: boolean;
  publish_queue_enabled: boolean;
  pending_publish_count: number;
  approved_publish_count: number;
  brief_markdown_preview: string;
  steps: PipelineStep[];
  links: Record<string, string>;
}

function stepTone(status: PipelineStep["status"]): "ok" | "warn" | "err" | "info" {
  if (status === "done") return "ok";
  if (status === "blocked" || status === "skipped") return "err";
  if (status === "running") return "info";
  return "warn";
}

const MORNING_PIPELINE_HINT = {
  title: { en: "Morning → Publish pipeline", sk: "Morning → Publish pipeline" },
  description: {
    en: "Phase D — Life OS brief, content draft, critic verify, Publish Queue approve. Cron tick 08:00 UTC.",
    sk: "Fáza D — Life OS brief, content draft, critic verify, schválenie v Publish Queue. Cron 08:00 UTC.",
  },
  options: {
    en: [
      "Bind Life OS + content routines to trio lanes.",
      "Run morning pipeline or wait for 08:00 UTC Celery tick.",
      "Approve packs in Publish Queue → Social simulate → live when ready.",
      "See docs/OPERATOR_FIRST_LIVE_POST.md for end-to-end checklist.",
    ],
    sk: [
      "Bind Life OS + content routines k trio lanes.",
      "Spusti morning pipeline alebo počkaj na Celery tick 08:00 UTC.",
      "Schváli pack v Publish Queue → Social simulate → live keď ready.",
      "Celý postup: docs/OPERATOR_FIRST_LIVE_POST.md.",
    ],
  },
};

function MorningPublishPipelinePanelInner() {
  const [snapshot, setSnapshot] = useState<MorningPublishPipelineSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [runBusy, setRunBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<MorningPublishPipelineSnapshot>("solo-operator/morning-publish-pipeline");
      setSnapshot(data);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Pipeline snapshot unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function runPipeline() {
    setRunBusy(true);
    try {
      await hivePostJson("solo-operator/morning-publish/run", { trigger_content: true });
      toast.success("Morning publish pipeline triggered");
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Pipeline run failed");
    } finally {
      setRunBusy(false);
    }
  }

  if (loading) {
    return (
      <p className="flex items-center gap-2 text-sm text-(--qs-muted)">
        <Loader2 className="size-4 animate-spin" aria-hidden /> Loading morning pipeline…
      </p>
    );
  }

  if (!snapshot?.enabled) {
    return (
      <V4Card id="morning-publish-pipeline">
        <V4CardHeader
          kicker="Phase D"
          title="Morning → Publish pipeline"
          description="Disabled via MORNING_PUBLISH_PIPELINE_ENABLED=false."
        />
      </V4Card>
    );
  }

  return (
    <V4Card id="morning-publish-pipeline">
      <V4CardHeader
        kicker="Phase D"
        title="Morning → Publish pipeline"
        description="Life OS brief → content draft → critic verify → Publish Queue approve (simulate-first)."
        actions={
          <InfoHint
            title={MORNING_PIPELINE_HINT.title}
            description={MORNING_PIPELINE_HINT.description}
            options={MORNING_PIPELINE_HINT.options}
          />
        }
      />
      {err ? <p className="mb-3 text-sm text-(--qs-red)">{err}</p> : null}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <V4Badge tone={snapshot.life_os_bound ? "ok" : "warn"}>
          Life OS {snapshot.life_os_bound ? "bound" : "unbound"}
        </V4Badge>
        <V4Badge tone={snapshot.content_routine_bound ? "ok" : "warn"}>
          Content {snapshot.content_routine_bound ? "bound" : "unbound"}
        </V4Badge>
        <V4Badge tone={snapshot.pending_publish_count > 0 ? "warn" : "ok"}>
          {snapshot.pending_publish_count} pending · {snapshot.approved_publish_count} approved
        </V4Badge>
        <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" disabled={runBusy} onClick={() => void runPipeline()}>
          {runBusy ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" aria-hidden />}
          Run morning pipeline
        </button>
        <Link href={snapshot.links.publish_queue ?? "/integrations?tab=studio"} className="qs-btn qs-btn--ghost qs-btn--sm">
          <Sunrise className="size-4" aria-hidden />
          Publish Queue
        </Link>
      </div>
      <ol className="space-y-2">
        {snapshot.steps.map((step) => (
          <li
            key={step.id}
            className={cn(
              "rounded-lg border border-(--qs-border) bg-black/20 px-3 py-3 text-sm",
              step.status === "done" && "border-(--qs-green)/30",
            )}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-semibold text-(--qs-text)">
                {step.scheduled_at} · {step.label}
              </span>
              <V4Badge tone={stepTone(step.status)}>{step.status}</V4Badge>
            </div>
            <p className="mt-1 text-(--qs-muted)">{step.detail}</p>
            {step.routine_name ? (
              <p className="mt-1 font-mono text-xs text-cyan">Routine: {step.routine_name}</p>
            ) : null}
            {step.last_session_status ? (
              <p className="mt-1 font-mono text-xs text-(--qs-text-3)">Last session: {step.last_session_status}</p>
            ) : null}
          </li>
        ))}
      </ol>
      {snapshot.brief_markdown_preview ? (
        <pre className="mt-4 max-h-48 overflow-auto rounded-lg border border-(--qs-border) bg-black/30 p-3 font-mono text-xs leading-relaxed text-(--qs-text)">
          {snapshot.brief_markdown_preview}
        </pre>
      ) : null}
    </V4Card>
  );
}

export const MorningPublishPipelinePanel = memo(MorningPublishPipelinePanelInner);
MorningPublishPipelinePanel.displayName = "MorningPublishPipelinePanel";

const LazyMorningPublishPipelinePanel = dynamic(
  () => Promise.resolve({ default: MorningPublishPipelinePanel }),
  {
    ssr: false,
    loading: () => (
      <p className="flex items-center gap-2 text-sm text-(--qs-muted)">
        <Loader2 className="size-4 animate-spin" aria-hidden /> Loading morning pipeline…
      </p>
    ),
  },
);

export { LazyMorningPublishPipelinePanel };
