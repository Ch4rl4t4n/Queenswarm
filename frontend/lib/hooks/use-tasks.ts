"use client";

import useSWR from "swr";

import { hiveGet } from "@/lib/api";
import { COCKPIT_POLL_AGENTS_TASKS_MS } from "@/lib/cockpit-poll-profile";
import { useSwrVisiblePollOptions } from "@/lib/hooks/use-swr-refresh-interval";
import type { TaskRow } from "@/lib/hive-types";

export function useTasks(params: string, refreshMs: number = COCKPIT_POLL_AGENTS_TASKS_MS): {
  tasks: TaskRow[] | undefined;
  error: Error | undefined;
  isLoading: boolean;
  mutate: () => void;
} {
  const key = params ? `phase-g/tasks?${params}` : null;
  const pollOptions = useSwrVisiblePollOptions(refreshMs);
  const { data, error, isLoading, mutate } = useSWR<TaskRow[]>(
    key,
    () => hiveGet<TaskRow[]>(`/tasks?${params}`),
    pollOptions,
  );
  return { tasks: data, error, isLoading, mutate };
}
