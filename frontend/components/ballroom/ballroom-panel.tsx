"use client";

import { MicIcon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { buildHiveWebsocketHref } from "@/lib/public-ws";

interface TranscriptLine {
  agent?: string;
  text?: string;
  type?: string;
}

export function BallroomPanel() {
  const [connected, setConnected] = useState(false);
  const [lines, setLines] = useState<TranscriptLine[]>([]);
  const [error, setError] = useState<string | null>(null);

  const appendLine = useCallback((line: TranscriptLine) => {
    setLines((prev) => [...prev.slice(-140), line]);
  }, []);

  const wsUrlFromSession = useCallback((sessionId: string): string => {
    if (typeof window === "undefined") {
      return "";
    }
    const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? `${window.location.origin}/api/v1`;
    const built = buildHiveWebsocketHref(apiBase, "/ballroom/ws/stream");
    const fallbackPath = "/api/v1/ballroom/ws/stream";
    const base =
      built ??
      `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}${fallbackPath}`;
    const url = new URL(base);
    url.searchParams.set("session_id", sessionId);
    const guestAllowed = process.env.NEXT_PUBLIC_BALLROOM_GUEST_WS === "true";
    if (!guestAllowed) {
      const tok = window.sessionStorage.getItem("hive_jwt_optional");
      if (tok) {
        url.searchParams.set("token", tok);
      }
    }
    return url.toString();
  }, []);

  const startSession = useCallback(async () => {
    setError(null);
    try {
      const res = await fetch("/api/proxy/ballroom/session", {
        method: "POST",
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const body = (await res.json()) as { session_id: string };
      const wsUrl = wsUrlFromSession(body.session_id);
      if (!wsUrl) {
        throw new Error("ws_url_unavailable");
      }
      const ws = new WebSocket(wsUrl);
      ws.onopen = () => setConnected(true);
      ws.onmessage = (evt) => {
        try {
          const row = JSON.parse(evt.data as string) as TranscriptLine;
          if (row?.type?.startsWith("ballroom.") || row.text) {
            appendLine(row);
          }
        } catch {
          appendLine({ type: "parse_error", text: String(evt.data) });
        }
      };
      ws.onerror = () => setError("ballroom websocket error");
      ws.onclose = () => setConnected(false);
      (window as Window & { __qs_ballroom_ws?: WebSocket }).__qs_ballroom_ws?.close?.();
      (window as Window & { __qs_ballroom_ws?: WebSocket }).__qs_ballroom_ws = ws;
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "session_failed");
    }
  }, [appendLine, wsUrlFromSession]);

  useEffect(() => () => (window as Window & { __qs_ballroom_ws?: WebSocket }).__qs_ballroom_ws?.close?.(), []);

  return (
    <div className="space-y-6 rounded-3xl border border-alert/35 bg-black/35 p-6 shadow-[0_0_42px_rgba(255,0,170,0.25)]">
      <header className="space-y-2">
        <h1 className="font-[family-name:var(--font-space-grotesk)] text-2xl font-semibold text-alert">
          ballroom bridge
        </h1>
        <p className="font-[family-name:var(--font-jetbrains-mono)] text-sm text-cyan">
          Stub Pipecat / WebRTC · multi-agent narration channel with Redis-grade fan-out to browsers.
        </p>
      </header>
      <button
        type="button"
        onClick={() => void startSession()}
        className="inline-flex items-center gap-3 rounded-full border border-pollen/60 px-6 py-3 font-[family-name:var(--font-jetbrains-mono)] text-xs uppercase tracking-[0.28em] text-pollen shadow-[0_0_28px_rgba(255,184,0,0.42)] transition hover:bg-pollen hover:text-black"
      >
        <MicIcon aria-hidden className="h-5 w-5" /> join ballroom capsule
      </button>
      <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-[#CCFFFF]/80">
        status:{" "}
        <span className={connected ? "text-success" : "text-danger"}>
          {connected ? "webrtc_lane_ready_stub" : "idle"}
        </span>
      </p>
      {error ? (
        <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-danger">{error}</p>
      ) : null}

      <div className="max-h-[460px] space-y-3 overflow-y-auto rounded-2xl border border-cyan/15 bg-black/45 p-4">
        <h2 className="font-[family-name:var(--font-space-grotesk)] text-sm font-semibold text-data">
          live transcript
        </h2>
        <ul className="space-y-3 font-[family-name:var(--font-jetbrains-mono)] text-sm text-[#CAFFFF]">
          {lines.length === 0 ? (
            <li className="text-cyan/50">listening for ballroom.transcript payloads…</li>
          ) : (
            lines.map((ln, idx) => (
              <li key={`${idx}-${ln.type ?? ln.agent ?? ln.text ?? ""}`} className="border-l border-pollen/35 pl-3">
                {ln.agent ? <span className="text-alert">{ln.agent}</span> : null}{" "}
                <span>{ln.text ?? ln.type ?? "…"}</span>
              </li>
            ))
          )}
        </ul>
      </div>
      <footer className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-cyan/60">
        BALLROOM_GUEST_WS on the API allows transcript sockets without JWT; production voice bridges still need Pipecat +
        provider keys.
      </footer>
    </div>
  );
}
