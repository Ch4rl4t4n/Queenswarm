"use client";

import Link from "next/link";
import { Loader2, Play, Sun } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { LazyAgentOsPanel } from "@/components/hive/agent-os-panel";
import { LazyMorningPublishPipelinePanel } from "@/components/hive/morning-publish-pipeline-panel";
import { LazyOperatorLoopPanel } from "@/components/hive/operator-loop-panel";
import { LazyOperatorPublishOnboardingPanel } from "@/components/hive/operator-publish-onboarding-panel";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

interface TrioLane {
  lane_id: string;
  label: string;
  description: string;
  swarm_hint: string;
  routine_id: string | null;
  routine_name: string | null;
  binding: string;
  last_session_status: string | null;
}

interface TrioStatus {
  description: string;
  lanes_bound: number;
  lanes_total: number;
  lanes: TrioLane[];
}

interface MorningBrief {
  markdown: string;
  tech_health_score: number;
  lanes_bound: number;
}

/** Solo operator preset group — orchestrates existing routines, not a separate hive. */
export function SoloOperatorTrioPanel() {
  const [status, setStatus] = useState<TrioStatus | null>(null);
  const [brief, setBrief] = useState<MorningBrief | null>(null);
  const [loading, setLoading] = useState(true);
  const [runBusy, setRunBusy] = useState(false);
  const [briefBusy, setBriefBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const body = await hiveGet<TrioStatus>("solo-operator/trio");
      setStatus(body);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Trio status unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function runCycle() {
    setRunBusy(true);
    try {
      const body = await hivePostJson<{ triggered: { session_id: string; label: string }[]; skipped: unknown[] }>(
        "solo-operator/trio/run",
        {},
      );
      toast.success(`Triggered ${body.triggered.length} lane(s)`);
      await reload();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Run failed");
    } finally {
      setRunBusy(false);
    }
  }

  async function loadBrief() {
    setBriefBusy(true);
    try {
      const body = await hiveGet<MorningBrief>("solo-operator/morning-brief");
      setBrief(body);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Brief unavailable");
    } finally {
      setBriefBusy(false);
    }
  }

  if (loading) {
    return (
      <p className="flex items-center gap-2 text-sm text-(--qs-muted)">
        <Loader2 className="size-4 animate-spin" aria-hidden /> Loading trio…
      </p>
    );
  }

  return (
    <V4Card id="solo-trio">
      <V4CardHeader
        kicker="Solo preset"
        title="My 3 Bees — mini-swarm group"
        description={
          status?.description ??
          "Three lanes over existing supervisor routines. Does not replace or split your hive."
        }
      />
      {err ? <p className="mb-3 text-sm text-(--qs-red)">{err}</p> : null}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <V4Badge tone={(status?.lanes_bound ?? 0) >= 2 ? "ok" : "warn"}>
          {status?.lanes_bound ?? 0}/{status?.lanes_total ?? 3} lanes bound
        </V4Badge>
        <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" disabled={runBusy} onClick={() => void runCycle()}>
          {runBusy ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" aria-hidden />}
          Run today&apos;s cycle
        </button>
        <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" disabled={briefBusy} onClick={() => void loadBrief()}>
          {briefBusy ? <Loader2 className="size-4 animate-spin" /> : <Sun className="size-4" aria-hidden />}
          Morning brief
        </button>
      </div>
      <ul className="space-y-3">
        {(status?.lanes ?? []).map((lane) => (
          <li key={lane.lane_id} className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-semibold text-(--qs-text)">{lane.label}</span>
              <V4Badge tone={lane.binding === "missing" ? "warn" : "ok"}>{lane.binding}</V4Badge>
            </div>
            <p className="mt-1 text-(--qs-muted)">{lane.description}</p>
            {lane.routine_name ? (
              <p className="mt-1 font-mono text-xs text-cyan">Routine: {lane.routine_name}</p>
            ) : (
              <p className="mt-1 text-xs text-(--qs-muted)">
                No routine — build{" "}
                <Link href="/swarms/new" className="text-cyan underline">
                  {lane.swarm_hint}
                </Link>{" "}
                swarm template
              </p>
            )}
            {lane.last_session_status ? (
              <p className="mt-1 font-mono text-xs text-(--qs-text-3)">Last session: {lane.last_session_status}</p>
            ) : null}
          </li>
        ))}
      </ul>
      {brief?.markdown ? (
        <pre className="mt-4 max-h-80 overflow-auto rounded-lg border border-(--qs-border) bg-black/30 p-3 font-mono text-xs leading-relaxed text-(--qs-text)">
          {brief.markdown}
        </pre>
      ) : null}
      <div className="mt-6 space-y-6">
        <LazyOperatorLoopPanel />
        <LazyAgentOsPanel />
        <LazyOperatorPublishOnboardingPanel />
        <LazyMorningPublishPipelinePanel />
      </div>
    </V4Card>
  );
}
