"use client";

import useSWR from "swr";

import { hiveGet } from "@/lib/api";
import type { TaskRow } from "@/lib/hive-types";

export function useTasks(params: string, refreshMs: number = 5000): {
  tasks: TaskRow[] | undefined;
  error: Error | undefined;
  isLoading: boolean;
  mutate: () => void;
} {
  const key = params ? `phase-g/tasks?${params}` : null;
  const { data, error, isLoading, mutate } = useSWR<TaskRow[]>(
    key,
    () => hiveGet<TaskRow[]>(`/tasks?${params}`),
    { refreshInterval: refreshMs, revalidateOnFocus: true },
  );
  return { tasks: data, error, isLoading, mutate };
}
