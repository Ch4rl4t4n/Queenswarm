"use client";

import type { JSX } from "react";

import { Loader2Icon, RefreshCw } from "lucide-react";
import useSWR from "swr";

import { V4Badge, V4Card, V4CardHeader, V4Stat, V4IconBolt } from "@/components/ui/v4";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { hiveGet } from "@/lib/api";
import { COCKPIT_POLL_BOARD_MS } from "@/lib/cockpit-poll-profile";
import { useSwrVisiblePollOptions } from "@/lib/hooks/use-swr-refresh-interval";
import type { SupervisorControlSummaryRow } from "@/lib/hive-types";

/** Hybrid runtime counters — in-process vs durable Celery queue depth. */
export function AgentsRuntimeStatusStrip(): JSX.Element {
  const pollOptions = useSwrVisiblePollOptions(COCKPIT_POLL_BOARD_MS);
  const { data, error, isLoading, mutate } = useSWR<SupervisorControlSummaryRow>(
    "hive/agent-sessions-summary",
    () => hiveGet<SupervisorControlSummaryRow>("agents/sessions/summary"),
    pollOptions,
  );

  return (
    <V4Card className="p-4 md:p-5">
      <V4CardHeader
        as="h2"
        kicker="Phase 6.0"
        title="Hybrid runtime"
        description="In-process sessions run under the API worker; durable sessions enqueue Celery sub-agent steps."
        hint={sectionHintNode("agentsRuntime")}
      />
      {isLoading && !data ? (
        <div className="mt-4 flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin text-pollen" aria-hidden />
          Loading runtime counters…
        </div>
      ) : error ? (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-(--qs-red)/30 bg-(--qs-red)/10 px-3 py-3">
          <p className="text-sm text-(--qs-text-2)">Runtime counters unavailable.</p>
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5" onClick={() => void mutate()}>
            <RefreshCw className="h-3.5 w-3.5" aria-hidden />
            Retry
          </button>
        </div>
      ) : (
        <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <V4Stat
            label="In-process active"
            value={data?.inprocess_active_sessions ?? 0}
            icon={V4IconBolt}
            valueVariant="text"
          />
          <V4Stat
            label="Durable active"
            value={data?.durable_active_sessions ?? 0}
            icon={V4IconBolt}
            iconTone="purple"
            valueVariant="text"
          />
          <div className="rounded-xl border border-(--qs-border) bg-black/30 p-3">
            <p className="text-[10px] uppercase tracking-wide text-(--qs-text-3)">Celery queue</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-pollen">
              {data?.durable_queued_sub_agents ?? 0}
            </p>
            <p className="mt-1 text-[11px] text-(--qs-text-3)">sub-agents queued</p>
          </div>
          <div className="rounded-xl border border-(--qs-border) bg-black/30 p-3">
            <p className="text-[10px] uppercase tracking-wide text-(--qs-text-3)">Needs input</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="text-2xl font-semibold tabular-nums text-(--qs-text)">
                {data?.needs_input_sessions ?? 0}
              </span>
              {(data?.needs_input_sessions ?? 0) > 0 ? <V4Badge tone="warn">review</V4Badge> : null}
            </div>
            <p className="mt-1 text-[11px] text-(--qs-text-3)">
              {data?.running_sessions ?? 0} running · {data?.sessions_total ?? 0} total
            </p>
          </div>
        </div>
      )}
    </V4Card>
  );
}
