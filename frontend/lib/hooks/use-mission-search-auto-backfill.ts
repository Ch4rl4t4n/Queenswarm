"use client";

import { useEffect, useRef } from "react";

import { hivePostJson } from "@/lib/api";

const BACKFILL_STAGGER_MS = 2800;
const SESSION_GUARD_KEY = "qs_mission_index_backfill_requested";

/** Fire one-shot semantic index backfill after dashboard boot (server Redis dedupes). */
export function useMissionSearchAutoBackfill(enabled = true): void {
  const startedRef = useRef(false);

  useEffect(() => {
    if (!enabled || startedRef.current) {
      return;
    }
    if (typeof window === "undefined") {
      return;
    }
    if (sessionStorage.getItem(SESSION_GUARD_KEY) === "1") {
      return;
    }

    startedRef.current = true;
    const timer = window.setTimeout(() => {
      sessionStorage.setItem(SESSION_GUARD_KEY, "1");
      void hivePostJson("solo-operator/mission-search/backfill-auto", { limit: 200 }).catch(() => {
        sessionStorage.removeItem(SESSION_GUARD_KEY);
      });
    }, BACKFILL_STAGGER_MS);

    return () => window.clearTimeout(timer);
  }, [enabled]);
}
