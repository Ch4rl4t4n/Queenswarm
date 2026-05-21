"use client";

import useSWR from "swr";

import { hiveGet } from "@/lib/api";
import type { SubSwarmRow } from "@/lib/hive-types";
import { useSwrVisiblePollOptions } from "@/lib/hooks/use-swr-refresh-interval";

export function useSwarms(refreshMs: number = 15_000): {
  swarms: SubSwarmRow[] | undefined;
  error: Error | undefined;
  isLoading: boolean;
  mutate: () => void;
} {
  const pollOptions = useSwrVisiblePollOptions(refreshMs);
  const { data, error, isLoading, mutate } = useSWR<SubSwarmRow[]>(
    "phase-g/swarms",
    () => hiveGet<SubSwarmRow[]>("/swarms?limit=50"),
    pollOptions,
  );
  return { swarms: data, error, isLoading, mutate };
}
