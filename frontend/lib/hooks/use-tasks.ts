"use client";

import useSWR from "swr";

import { hiveGet } from "@/lib/api";
import { COCKPIT_POLL_AGENTS_TASKS_MS } from "@/lib/cockpit-poll-profile";
import type { TaskRow } from "@/lib/hive-types";

export function useTasks(params: string, refreshMs: number = COCKPIT_POLL_AGENTS_TASKS_MS): {
  tasks: TaskRow[] | undefined;
  error: Error | undefined;
  isLoading: boolean;
  mutate: () => void;
} {
  const key = params ? `phase-g/tasks?${params}` : null;
  const { data, error, isLoading, mutate } = useSWR<TaskRow[]>(
    key,
    () => hiveGet<TaskRow[]>(`/tasks?${params}`),
    {
      refreshInterval: refreshMs,
      revalidateOnFocus: true,
      dedupingInterval: Math.min(4_000, Math.floor(refreshMs * 0.6)),
      focusThrottleInterval: Math.max(refreshMs, 5_000),
    },
  );
  return { tasks: data, error, isLoading, mutate };
}
