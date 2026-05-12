"use client";

import useSWR from "swr";

import { hiveGet } from "@/lib/api";
import type { SubSwarmRow } from "@/lib/hive-types";

export function useSwarms(refreshMs: number = 15_000): {
  swarms: SubSwarmRow[] | undefined;
  error: Error | undefined;
  isLoading: boolean;
  mutate: () => void;
} {
  const { data, error, isLoading, mutate } = useSWR<SubSwarmRow[]>(
    "phase-g/swarms",
    () => hiveGet<SubSwarmRow[]>("/swarms?limit=50"),
    { refreshInterval: refreshMs, revalidateOnFocus: true },
  );
  return { swarms: data, error, isLoading, mutate };
}
