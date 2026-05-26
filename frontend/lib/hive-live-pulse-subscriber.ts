"use client";

import type { HiveLivePulsePayload } from "@/lib/cockpit-ws-delta";
import { resolveHiveBearerToken } from "@/lib/hive-bearer-token";
import { buildHiveWebsocketHref } from "@/lib/public-ws";

type HiveLivePulseListener = (pulse: HiveLivePulsePayload) => void;

const WS_RECONNECT_MS = 5_000;

const listeners = new Set<HiveLivePulseListener>();
let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let connecting = false;
let connected = false;
let lastRevision = 0;

function notifyListeners(pulse: HiveLivePulsePayload): void {
  for (const listener of listeners) {
    listener(pulse);
  }
}

async function ensureHiveLiveConnection(): Promise<void> {
  if (typeof window === "undefined" || ws || connecting) {
    return;
  }
  connecting = true;

  try {
    const guest = process.env.NEXT_PUBLIC_HIVE_WS_GUEST === "true";
    const token = guest ? null : await resolveHiveBearerToken();
    const base = process.env.NEXT_PUBLIC_API_BASE ?? `${window.location.origin}/api/v1`;
    const raw = buildHiveWebsocketHref(base, "/ws/live");
    if (!raw) {
      return;
    }

    const url = new URL(raw);
    if (!guest && token) {
      url.searchParams.set("token", token);
    }

    ws = new WebSocket(url.toString());

    ws.onopen = () => {
      connected = true;
    };

    ws.onclose = () => {
      connected = false;
      ws = null;
      if (listeners.size > 0) {
        reconnectTimer = setTimeout(() => {
          void ensureHiveLiveConnection();
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
        if (revision <= lastRevision) {
          return;
        }
        lastRevision = revision;
        notifyListeners(data);
      } catch {
        /* ignore malformed frames */
      }
    };
  } finally {
    connecting = false;
  }
}

/** Shared `/ws/live` fan-out — one socket per tab for cockpit + operator pending hooks. */
export function subscribeHiveLivePulse(listener: HiveLivePulseListener): () => void {
  listeners.add(listener);
  void ensureHiveLiveConnection();
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      ws?.close();
      ws = null;
      connected = false;
    }
  };
}

/** Whether the shared hive live socket is currently open. */
export function isHiveLivePulseConnected(): boolean {
  return connected;
}
