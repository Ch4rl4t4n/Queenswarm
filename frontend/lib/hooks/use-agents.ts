"use client";

import useSWR from "swr";

import { hiveGet } from "@/lib/api";
import type { AgentRow } from "@/lib/hive-types";

const DEFAULT_POLL_MS = 5000;

export function useAgents(refreshMs: number = DEFAULT_POLL_MS): {
  agents: AgentRow[] | undefined;
  error: Error | undefined;
  isLoading: boolean;
  mutate: () => void;
} {
  const { data, error, isLoading, mutate } = useSWR<AgentRow[]>(
    "phase-g/agents",
    () => hiveGet<AgentRow[]>("/agents?limit=200"),
    { refreshInterval: refreshMs, revalidateOnFocus: true }, // Phase G2: hive poll cadence ≈ rapid loop UX
  );
  return { agents: data, error, isLoading, mutate };
}
