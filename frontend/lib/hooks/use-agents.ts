"use client";

import useSWR from "swr";

import { hiveGet } from "@/lib/api";
import type { AgentRow } from "@/lib/hive-types";

export function useAgents(refreshMs: number = 5000): {
  agents: AgentRow[] | undefined;
  error: Error | undefined;
  isLoading: boolean;
  mutate: () => void;
} {
  const { data, error, isLoading, mutate } = useSWR<AgentRow[]>(
    "phase-g/agents",
    () => hiveGet<AgentRow[]>("/agents?limit=200"),
    { refreshInterval: refreshMs, revalidateOnFocus: true },
  );
  return { agents: data, error, isLoading, mutate };
}
