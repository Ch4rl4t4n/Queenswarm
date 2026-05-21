"use client";

import { useEffect, useRef, useState } from "react";

import type { HiveLivePulsePayload } from "@/lib/cockpit-ws-delta";
import { resolveHiveBearerToken } from "@/lib/hive-bearer-token";
import { buildHiveWebsocketHref } from "@/lib/public-ws";

interface UseCockpitLivePulseOptions {
  readonly enabled: boolean;
  readonly onPulse: (pulse: HiveLivePulsePayload) => void;
}

const WS_RECONNECT_MS = 5_000;

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

    let alive = true;
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    async function connect(): Promise<void> {
      const guest = process.env.NEXT_PUBLIC_HIVE_WS_GUEST === "true";
      const token = guest ? null : await resolveHiveBearerToken();
      const base = process.env.NEXT_PUBLIC_API_BASE ?? `${window.location.origin}/api/v1`;
      const raw = buildHiveWebsocketHref(base, "/ws/live");
      if (!raw || !alive) {
        return;
      }

      const url = new URL(raw);
      if (!guest && token) {
        url.searchParams.set("token", token);
      }

      ws = new WebSocket(url.toString());

      ws.onopen = () => {
        if (alive) {
          setConnected(true);
        }
      };

      ws.onclose = () => {
        if (alive) {
          setConnected(false);
          reconnectTimer = setTimeout(() => {
            void connect();
          }, WS_RECONNECT_MS);
        }
      };

      ws.onerror = () => {
        ws?.close();
      };

      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data as string) as HiveLivePulsePayload;
          if (data.type !== "hive.snapshot") {
            return;
          }
          const revision = typeof data.revision === "number" ? data.revision : Date.now();
          if (revision <= lastRevisionRef.current) {
            return;
          }
          lastRevisionRef.current = revision;
          onPulseRef.current(data);
        } catch {
          /* ignore malformed frames */
        }
      };
    }

    void connect();

    return () => {
      alive = false;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      ws?.close();
      setConnected(false);
    };
  }, [enabled]);

  return connected;
}
