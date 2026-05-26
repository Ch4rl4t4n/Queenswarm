"use client";

import { useEffect, useState } from "react";
import type { SWRConfiguration } from "swr";

import { isHiveApiRateLimited } from "@/lib/api";
import { subscribeHiveApiRateLimit } from "@/lib/hive-api-rate-limit-bus";
import { isHiveSessionDead } from "@/lib/hive-session-guard";
import { useDocumentVisible } from "@/lib/hooks/use-document-visible";

/**
 * SWR `refreshInterval` that drops to 0 while the browser tab is hidden.
 * Pass `null` or `0` to disable polling entirely.
 */
export function useSwrRefreshInterval(baseMs: number | null | undefined): number {
  const visible = useDocumentVisible();
  const [, setRateLimitTick] = useState(0);

  useEffect(() => subscribeHiveApiRateLimit(() => setRateLimitTick((n) => n + 1)), []);

  if (!visible || baseMs == null || baseMs <= 0 || isHiveApiRateLimited() || isHiveSessionDead()) {
    return 0;
  }
  return baseMs;
}

/**
 * Build SWR options with visibility-aware polling and sensible dedupe defaults.
 */
export function swrVisiblePollOptions(refreshMs: number): Pick<
  SWRConfiguration,
  "refreshInterval" | "revalidateOnFocus" | "dedupingInterval" | "focusThrottleInterval"
> {
  return {
    refreshInterval: refreshMs,
    revalidateOnFocus: false,
    dedupingInterval: Math.min(6_000, Math.floor(refreshMs * 0.75)),
    focusThrottleInterval: Math.max(refreshMs * 2, 15_000),
  };
}

/** Hook wrapper — use inside client components that call `useSWR`. */
export function useSwrVisiblePollOptions(refreshMs: number): Pick<
  SWRConfiguration,
  "refreshInterval" | "revalidateOnFocus" | "dedupingInterval" | "focusThrottleInterval"
> {
  const refreshInterval = useSwrRefreshInterval(refreshMs);
  return swrVisiblePollOptions(refreshInterval);
}
