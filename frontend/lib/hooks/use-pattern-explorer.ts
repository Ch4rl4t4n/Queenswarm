"use client";

import { useCallback, useEffect, useState } from "react";

import { usePlatform } from "@/components/hive/platform-context";
import { COCKPIT_POLL_COLONY_TELEMETRY_MS } from "@/lib/cockpit-poll-profile";
import { DASHBOARD_BOOT_STAGGER_MS } from "@/lib/dashboard-boot-stagger";
import { HiveApiError, hiveGet } from "@/lib/api";
import type { PatternExplorerPayload } from "@/lib/hive-types";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";

export function usePatternExplorerData(poll: boolean): {
  loading: boolean;
  err: string | null;
  data: PatternExplorerPayload | null;
  reload: () => Promise<void>;
} {
  const { hasFeature } = usePlatform();
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [data, setData] = useState<PatternExplorerPayload | null>(null);

  const load = useCallback(async () => {
    if (!hasFeature("pattern_explorer")) {
      setLoading(false);
      return;
    }
    try {
      const body = await hiveGet<PatternExplorerPayload>("harness/pattern-explorer");
      setData(body);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Pattern Explorer unavailable.");
    } finally {
      setLoading(false);
    }
  }, [hasFeature]);

  useEffect(() => {
    void load();
  }, [load]);

  useIntervalWhenVisible(() => void load(), COCKPIT_POLL_COLONY_TELEMETRY_MS, {
    enabled: poll && hasFeature("pattern_explorer"),
    initialDelayMs: DASHBOARD_BOOT_STAGGER_MS.patternExplorer,
  });

  return { loading, err, data, reload: load };
}
