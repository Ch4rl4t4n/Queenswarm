"use client";

import useSWR from "swr";

import { hiveGet } from "@/lib/api";
import { COCKPIT_PERF } from "@/lib/cockpit-performance-budget";
import { cockpitSwrKeys } from "@/lib/cockpit-swr-keys";
import { COCKPIT_POLL_AGENTS_TASKS_MS } from "@/lib/cockpit-poll-profile";
import { useSwrVisiblePollOptions } from "@/lib/hooks/use-swr-refresh-interval";
import type { AgentRow } from "@/lib/hive-types";

export function useAgents(refreshMs: number = COCKPIT_POLL_AGENTS_TASKS_MS): {
  agents: AgentRow[] | undefined;
  error: Error | undefined;
  isLoading: boolean;
  mutate: () => void;
} {
  const pollOptions = useSwrVisiblePollOptions(refreshMs);
  const { data, error, isLoading, mutate } = useSWR<AgentRow[]>(
    cockpitSwrKeys.agentsFull(),
    () => hiveGet<AgentRow[]>(`agents?limit=${COCKPIT_PERF.fullAgentsLimit}`),
    { ...pollOptions, keepPreviousData: true },
  );
  return { agents: data, error, isLoading, mutate };
}
