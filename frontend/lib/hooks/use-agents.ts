"use client";

import useSWR from "swr";

import { hiveGet } from "@/lib/api";
import type { AgentRow } from "@/lib/hive-types";
import { COCKPIT_POLL_AGENTS_TASKS_MS } from "@/lib/cockpit-poll-profile";

export function useAgents(refreshMs: number = COCKPIT_POLL_AGENTS_TASKS_MS): {
  agents: AgentRow[] | undefined;
  error: Error | undefined;
  isLoading: boolean;
  mutate: () => void;
} {
  const { data, error, isLoading, mutate } = useSWR<AgentRow[]>(
    "phase-g/agents",
    () => hiveGet<AgentRow[]>("/agents?limit=200"),
    {
      refreshInterval: refreshMs,
      revalidateOnFocus: true,
      dedupingInterval: Math.min(4_000, Math.floor(refreshMs * 0.6)),
      focusThrottleInterval: Math.max(refreshMs, 5_000),
    }, // Phase G2: hive poll cadence ≈ rapid loop UX
  );
  return { agents: data, error, isLoading, mutate };
}
