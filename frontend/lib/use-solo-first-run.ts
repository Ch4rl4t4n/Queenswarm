"use client";

import { useCallback, useEffect, useState } from "react";

import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

export interface FirstRunStep {
  id: string;
  label: string;
  detail: string;
  done: boolean;
  href: string;
  link_label: string;
}

export interface FirstRunCapability {
  headline: string;
  subhead: string;
  bullets: string[];
}

export interface FirstRunSnapshot {
  enabled: boolean;
  complete: boolean;
  progress_pct: number;
  steps: FirstRunStep[];
  capability?: FirstRunCapability;
}

interface UseSoloFirstRunOptions {
  /** When false, skips fetch (e.g. non-solo mode). */
  enabled?: boolean;
}

interface UseSoloFirstRunResult {
  data: FirstRunSnapshot | null;
  loading: boolean;
  error: string | null;
  briefBusy: boolean;
  reload: () => Promise<void>;
  applyStarterBrief: () => Promise<boolean>;
}

export function useSoloFirstRun(options: UseSoloFirstRunOptions = {}): UseSoloFirstRunResult {
  const { enabled = true } = options;
  const [data, setData] = useState<FirstRunSnapshot | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);
  const [briefBusy, setBriefBusy] = useState(false);

  const reload = useCallback(async () => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const body = await hiveGet<FirstRunSnapshot>("solo-operator/first-run");
      setData(body);
    } catch (e) {
      const message = e instanceof HiveApiError ? e.message : "First-run checklist unavailable";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const applyStarterBrief = useCallback(async (): Promise<boolean> => {
    setBriefBusy(true);
    try {
      const result = await hivePostJson<{ ok: boolean; applied?: boolean }>(
        "solo-operator/first-run/starter-brief",
        {},
      );
      await reload();
      return result.applied === true;
    } finally {
      setBriefBusy(false);
    }
  }, [reload]);

  return { data, loading, error, briefBusy, reload, applyStarterBrief };
}
