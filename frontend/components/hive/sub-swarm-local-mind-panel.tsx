"use client";

import { Loader2Icon, RadioIcon, RefreshCwIcon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Chip } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { SubSwarmLocalMindDetail } from "@/lib/hive-types";
import { formatSyncDue, memberCapacityTone, syncTone } from "@/lib/sub-swarm-local-mind-utils";
import { cn } from "@/lib/utils";

interface SubSwarmLocalMindPanelProps {
  readonly swarmId: string;
  readonly onSynced?: () => void;
}

/** Local hive mind detail — memory highlights + 5 min global sync ring. */
export function SubSwarmLocalMindPanel({ swarmId, onSynced }: SubSwarmLocalMindPanelProps): JSX.Element {
  const [mind, setMind] = useState<SubSwarmLocalMindDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncBusy, setSyncBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const payload = await hiveGet<SubSwarmLocalMindDetail>(`swarms/${swarmId}/local-mind`);
      setMind(payload);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Local mind unavailable.");
      setMind(null);
    } finally {
      setLoading(false);
    }
  }, [swarmId]);

  useEffect(() => {
    void load();
  }, [load]);

  const ackSync = useCallback(async () => {
    setSyncBusy(true);
    try {
      await hivePostJson(`swarms/${swarmId}/global-sync`, {});
      toast.success("Global sync checkpoint recorded.");
      await load();
      onSynced?.();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Sync ack failed.");
    } finally {
      setSyncBusy(false);
    }
  }, [load, onSynced, swarmId]);

  if (loading) {
    return (
      <p className="flex items-center gap-2 text-xs text-(--qs-text-3)">
        <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden /> Loading local hive mind…
      </p>
    );
  }

  if (!mind) {
    return <p className="text-xs text-(--qs-text-3)">Local mind snapshot unavailable.</p>;
  }

  const intervalMin = Math.round(mind.hive_sync_interval_sec / 60);

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
      <div className="rounded-xl border border-cyan/25 bg-cyan/5 p-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <RadioIcon className="h-4 w-4 text-cyan" aria-hidden />
            <p className="text-sm font-medium text-(--qs-text)">Global sync</p>
          </div>
          <V4Badge tone={syncTone(mind.needs_sync)}>{mind.needs_sync ? "sync due" : "in cadence"}</V4Badge>
        </div>

        <div className="relative mt-4 h-2 overflow-hidden rounded-full bg-white/10">
          <div
            className={cn("h-full rounded-full transition-all", mind.needs_sync ? "bg-pollen" : "bg-success")}
            style={{ width: `${mind.sync_progress_pct}%` }}
          />
        </div>

        <p className="mt-2 text-xs text-(--qs-text-3)">
          Every {intervalMin} min · next in{" "}
          <span className="font-mono text-cyan">{formatSyncDue(mind.sync_due_in_sec)}</span>
        </p>

        <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm mt-3 gap-2" disabled={syncBusy} onClick={() => void ackSync()}>
          {syncBusy ? <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <RefreshCwIcon className="h-3.5 w-3.5" aria-hidden />}
          Record global sync
        </button>
      </div>

      <div className="rounded-xl border border-(--qs-border) bg-white/[0.02] p-4">
        <p className="text-sm font-medium text-(--qs-text)">Local memory</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <V4Badge tone={memberCapacityTone(mind.member_count, mind.recommended_bee_count)}>
            {mind.member_count}/{mind.recommended_bee_count} bees
          </V4Badge>
          {mind.wizard_template ? <V4Chip type="span">template · {mind.wizard_template}</V4Chip> : null}
          {mind.swarm_role_label ? <V4Chip type="span">{mind.swarm_role_label}</V4Chip> : null}
          <V4Chip type="span">{mind.memory_key_count} keys</V4Chip>
        </div>
        {mind.goal_preview ? <p className="mt-3 text-xs text-(--qs-text-2)">Goal: {mind.goal_preview}</p> : null}
        {mind.last_waggle_cue ? (
          <p className="mt-2 text-xs text-pollen">Last waggle: {mind.last_waggle_cue}</p>
        ) : (
          <p className="mt-2 text-xs text-(--qs-text-3)">No local waggle cue yet — run a workflow to populate memory.</p>
        )}
      </div>
    </div>
  );
}
