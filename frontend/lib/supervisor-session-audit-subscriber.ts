"use client";

import { resolveHiveBearerToken } from "@/lib/hive-bearer-token";
import { buildHiveWebsocketHref } from "@/lib/hive-ws-url";
import type { SupervisorSessionAuditLogRow } from "@/lib/hive-types";

type AuditEntryListener = (entry: SupervisorSessionAuditLogRow) => void;
export type SupervisorAuditConnectionState = "idle" | "connecting" | "live" | "reconnecting";
type ConnectionStateListener = (state: SupervisorAuditConnectionState) => void;

interface SessionChannel {
  listeners: Set<AuditEntryListener>;
  stateListeners: Set<ConnectionStateListener>;
  ws: WebSocket | null;
  reconnectTimer: ReturnType<typeof setTimeout> | null;
  reconnectAttempt: number;
  connecting: boolean;
  connectionState: SupervisorAuditConnectionState;
}

const RECONNECT_BASE_MS = 1_000;
const RECONNECT_MAX_MS = 30_000;

const channels = new Map<string, SessionChannel>();

function reconnectDelayMs(attempt: number): number {
  return Math.min(RECONNECT_MAX_MS, RECONNECT_BASE_MS * 2 ** attempt);
}

function getChannel(sessionId: string): SessionChannel {
  const existing = channels.get(sessionId);
  if (existing) {
    return existing;
  }
  const created: SessionChannel = {
    listeners: new Set(),
    stateListeners: new Set(),
    ws: null,
    reconnectTimer: null,
    reconnectAttempt: 0,
    connecting: false,
    connectionState: "idle",
  };
  channels.set(sessionId, created);
  return created;
}

function clearReconnectTimer(channel: SessionChannel): void {
  if (channel.reconnectTimer !== null) {
    clearTimeout(channel.reconnectTimer);
    channel.reconnectTimer = null;
  }
}

function setConnectionState(sessionId: string, state: SupervisorAuditConnectionState): void {
  const channel = channels.get(sessionId);
  if (!channel || channel.connectionState === state) {
    return;
  }
  channel.connectionState = state;
  for (const listener of channel.stateListeners) {
    listener(state);
  }
}

function notifyListeners(sessionId: string, entry: SupervisorSessionAuditLogRow): void {
  const channel = channels.get(sessionId);
  if (!channel) {
    return;
  }
  for (const listener of channel.listeners) {
    listener(entry);
  }
}

function scheduleReconnect(sessionId: string): void {
  const channel = channels.get(sessionId);
  if (!channel || channel.listeners.size === 0) {
    return;
  }
  setConnectionState(sessionId, "reconnecting");
  clearReconnectTimer(channel);
  const delay = reconnectDelayMs(channel.reconnectAttempt);
  channel.reconnectAttempt += 1;
  channel.reconnectTimer = setTimeout(() => {
    void ensureSessionConnection(sessionId);
  }, delay);
}

async function ensureSessionConnection(sessionId: string): Promise<void> {
  const channel = getChannel(sessionId);
  if (typeof window === "undefined" || channel.ws || channel.connecting || channel.listeners.size === 0) {
    return;
  }
  channel.connecting = true;
  setConnectionState(sessionId, "connecting");

  try {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? `${window.location.origin}/api/v1`;
    const built = buildHiveWebsocketHref(
      apiBase,
      `agents/sessions/${encodeURIComponent(sessionId)}/audit-live`,
    );
    if (!built) {
      scheduleReconnect(sessionId);
      return;
    }

    const url = new URL(built);
    const token = await resolveHiveBearerToken();
    if (token) {
      url.searchParams.set("token", token);
    }

    const ws = new WebSocket(url.toString());
    channel.ws = ws;

    ws.onopen = () => {
      channel.reconnectAttempt = 0;
      setConnectionState(sessionId, "live");
    };

    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data as string) as {
          type?: string;
          entry?: SupervisorSessionAuditLogRow;
        };
        if (data.type !== "supervisor_session.audit" || !data.entry) {
          return;
        }
        notifyListeners(sessionId, data.entry);
      } catch {
        /* ignore malformed frames */
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    ws.onclose = () => {
      channel.ws = null;
      scheduleReconnect(sessionId);
    };
  } finally {
    channel.connecting = false;
  }
}

function teardownSessionIfIdle(sessionId: string): void {
  const channel = channels.get(sessionId);
  if (!channel || channel.listeners.size > 0) {
    return;
  }
  clearReconnectTimer(channel);
  channel.ws?.close();
  setConnectionState(sessionId, "idle");
  channels.delete(sessionId);
}

/** Shared audit-live socket per supervisor session — one connection per session per tab. */
export function subscribeSupervisorSessionAudit(
  sessionId: string,
  listener: AuditEntryListener,
): () => void {
  if (!sessionId) {
    return () => undefined;
  }
  const channel = getChannel(sessionId);
  channel.listeners.add(listener);
  void ensureSessionConnection(sessionId);
  return () => {
    channel.listeners.delete(listener);
    teardownSessionIfIdle(sessionId);
  };
}

/** Observe live/reconnecting audit websocket state for one supervisor session. */
export function subscribeSupervisorSessionAuditConnectionState(
  sessionId: string,
  listener: ConnectionStateListener,
): () => void {
  if (!sessionId) {
    return () => undefined;
  }
  const channel = getChannel(sessionId);
  channel.stateListeners.add(listener);
  listener(channel.connectionState);
  void ensureSessionConnection(sessionId);
  return () => {
    channel.stateListeners.delete(listener);
    teardownSessionIfIdle(sessionId);
  };
}

/** Current audit websocket state for one supervisor session (idle when unsubscribed). */
export function getSupervisorSessionAuditConnectionState(
  sessionId: string,
): SupervisorAuditConnectionState {
  return channels.get(sessionId)?.connectionState ?? "idle";
}

/** Force reconnect for one supervisor session audit-live socket. */
export function reconnectSupervisorSessionAudit(sessionId: string): void {
  if (!sessionId || typeof window === "undefined") {
    return;
  }
  const channel = channels.get(sessionId);
  if (!channel || channel.listeners.size === 0) {
    return;
  }
  clearReconnectTimer(channel);
  channel.ws?.close();
  channel.ws = null;
  channel.reconnectAttempt = 0;
  setConnectionState(sessionId, "connecting");
  void ensureSessionConnection(sessionId);
}
