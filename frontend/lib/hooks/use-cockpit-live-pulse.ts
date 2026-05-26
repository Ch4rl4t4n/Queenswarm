"use client";

import { useEffect, useRef, useState } from "react";

import type { HiveLivePulsePayload } from "@/lib/cockpit-ws-delta";
import { isHiveLivePulseConnected, subscribeHiveLivePulse } from "@/lib/hive-live-pulse-subscriber";

interface UseCockpitLivePulseOptions {
  readonly enabled: boolean;
  readonly onPulse: (pulse: HiveLivePulsePayload) => void;
}

/**
 * Subscribe to `/ws/live` hive snapshots and deliver parsed pulse payloads.
 *
 * Returns whether the socket is currently connected (used to lengthen poll fallback).
 */
export function useCockpitLivePulse({ enabled, onPulse }: UseCockpitLivePulseOptions): boolean {
  const [connected, setConnected] = useState(false);
  const lastRevisionRef = useRef(0);
  const onPulseRef = useRef(onPulse);
  onPulseRef.current = onPulse;

  useEffect(() => {
    if (!enabled || typeof window === "undefined") {
      setConnected(false);
      return undefined;
    }

    const unsubscribe = subscribeHiveLivePulse((data) => {
      const revision = typeof data.revision === "number" ? data.revision : Date.now();
      if (revision <= lastRevisionRef.current) {
        return;
      }
      lastRevisionRef.current = revision;
      onPulseRef.current(data);
      setConnected(isHiveLivePulseConnected());
    });

    const syncTimer = window.setInterval(() => {
      setConnected(isHiveLivePulseConnected());
    }, 2_000);

    return () => {
      window.clearInterval(syncTimer);
      unsubscribe();
      setConnected(false);
    };
  }, [enabled]);

  return connected;
}
