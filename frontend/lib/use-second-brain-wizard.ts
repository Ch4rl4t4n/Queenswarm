"use client";

import { useCallback, useEffect, useState } from "react";

import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

export interface SecondBrainWizardStep {
  id: string;
  label: string;
  detail: string;
  done: boolean;
  href: string;
  link_label: string;
  progress_note: string | null;
}

export interface SecondBrainWizardSnapshot {
  enabled: boolean;
  complete: boolean;
  progress_pct: number;
  brain_pack_filled: number;
  brain_pack_total: number;
  trio_bound: number;
  trio_total: number;
  steps: SecondBrainWizardStep[];
}

export function useSecondBrainWizard(enabled: boolean): {
  data: SecondBrainWizardSnapshot | null;
  loading: boolean;
  seedBusy: boolean;
  reload: () => Promise<void>;
  seedBrainPack: () => Promise<boolean>;
} {
  const [data, setData] = useState<SecondBrainWizardSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [seedBusy, setSeedBusy] = useState(false);

  const reload = useCallback(async () => {
    if (!enabled) {
      return;
    }
    setLoading(true);
    try {
      const snap = await hiveGet<SecondBrainWizardSnapshot>("solo-operator/second-brain-wizard");
      setData(snap);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const seedBrainPack = useCallback(async (): Promise<boolean> => {
    setSeedBusy(true);
    try {
      const res = await hivePostJson<{ seeded_kinds: string[] }>("memory/curated/seed-brain-pack", {
        overwrite: false,
      });
      await reload();
      return (res.seeded_kinds ?? []).length > 0;
    } catch (e) {
      if (e instanceof HiveApiError) {
        throw e;
      }
      throw new HiveApiError("Could not seed Brain Pack.", 500, null);
    } finally {
      setSeedBusy(false);
    }
  }, [reload]);

  return { data, loading, seedBusy, reload, seedBrainPack };
}
