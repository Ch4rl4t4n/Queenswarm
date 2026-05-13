"use client";

import { MicIcon, MicOffIcon } from "lucide-react";
import type { CSSProperties } from "react";
import { useCallback, useEffect, useRef, useState } from "react";

import { buildHiveWebsocketHref } from "@/lib/public-ws";
import { cn } from "@/lib/utils";

interface SessionCapsule {
  session_id: string;
  ws_url?: string;
  ws_url_path?: string;
}

interface BallroomBubble {
  id: string;
  agent: string;
  text: string;
  timestamp: string;
  variant: "agent" | "user" | "system";
}

interface SessionAgentRow {
  id?: string;
  name: string;
  role?: string;
}

const AGENT_ACCENTS: Record<string, string> = {
  Orchestrator: "#FFB800",
  Scout: "#00E5FF",
  Eval: "#FFB800",
  Sim: "#FF00AA",
  Action: "#00FF88",
  Queen: "#FFB800",
  System: "#5a5a7a",
};

function accentForName(name: string): string {
  const n = name.trim();
  const direct = AGENT_ACCENTS[n];
  if (direct) {
    return direct;
  }
  const token = n.split(/\s+/)[0];
  const first = token && AGENT_ACCENTS[token] ? AGENT_ACCENTS[token] : undefined;
  return first ?? "#9898b8";
}

export function BallroomPanel() {
  const [connected, setConnected] = useState(false);
  const [starting, setStarting] = useState(false);
  const [messages, setMessages] = useState<BallroomBubble[]>([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [muted, setMuted] = useState(false);
  const mutedRef = useRef(false);
  const [speaking, setSpeaking] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const sessionIdRef = useRef<string | null>(null);
  const [sessionLabel, setSessionLabel] = useState<string | null>(null);
  const [sessionAgents, setSessionAgents] = useState<SessionAgentRow[]>([]);
  const sessionAgentsRef = useRef<SessionAgentRow[]>([]);

  useEffect(() => {
    mutedRef.current = muted;
  }, [muted]);

  useEffect(() => {
    sessionAgentsRef.current = sessionAgents;
  }, [sessionAgents]);

  useEffect(() => {
    void fetch("/api/proxy/agents", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d: unknown) => {
        if (!d) {
          return;
        }
        const raw = d as Record<string, unknown>;
        const all = (
          Array.isArray(d)
            ? d
            : (Array.isArray(raw.agents)
                ? raw.agents
                : Array.isArray(raw.items)
                  ? raw.items
                  : [])
        ) as Record<string, unknown>[];
        const normalized: SessionAgentRow[] = all.map((a) => ({
          id: typeof a.id === "string" ? a.id : a.id !== undefined && a.id !== null ? String(a.id) : undefined,
          name: typeof a.name === "string" ? a.name : "Agent",
          role: typeof a.role === "string" ? a.role : undefined,
        }));
        const managers = normalized.filter((a) => {
          const nl = a.name.toLowerCase();
          const rl = (a.role ?? "").toLowerCase();
          return (
            nl.includes("manager") ||
            nl.includes("orchestrator") ||
            rl.includes("manager") ||
            rl.includes("orchestrator")
          );
        });
        setSessionAgents(managers.length > 0 ? managers.slice(0, 10) : normalized.slice(0, 10));
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const appendBubble = useCallback((patch: Omit<BallroomBubble, "id">) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
    setMessages((prev) => [...prev.slice(-240), { ...patch, id }]);
  }, []);

  const wsUrlFromSessionCapsule = useCallback((capsule: SessionCapsule): string => {
    if (typeof window === "undefined") {
      return "";
    }
    const guestAllowed = process.env.NEXT_PUBLIC_BALLROOM_GUEST_WS === "true";
    const token = guestAllowed ? null : window.sessionStorage.getItem("hive_jwt_optional");

    const pathStyle =
      typeof capsule.ws_url_path === "string" && capsule.ws_url_path.startsWith("/")
        ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}${capsule.ws_url_path}`
        : "";

    const streamStyle = (() => {
      const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? `${window.location.origin}/api/v1`;
      const built = buildHiveWebsocketHref(apiBase, "/ballroom/ws/stream");
      const fallbackPath = "/api/v1/ballroom/ws/stream";
      const base =
        built ?? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}${fallbackPath}`;
      const url = new URL(base);
      url.searchParams.set("session_id", capsule.session_id);
      return url.toString();
    })();

    const pick = pathStyle || streamStyle;
    const url = new URL(pick);
    if (token) {
      url.searchParams.set("token", token);
    }
    return url.toString();
  }, []);

  const bindWebSocketToCapsule = useCallback(
    (capsule: SessionCapsule) => {
      setError(null);
      sessionIdRef.current = capsule.session_id;
      setSessionLabel(capsule.session_id);

      const wsUrl = wsUrlFromSessionCapsule(capsule);
      if (!wsUrl) {
        setError("ws_url_unavailable");
        return;
      }

      wsRef.current?.close();
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);

      ws.onmessage = (evt) => {
        try {
          const row = JSON.parse(evt.data as string) as Record<string, unknown>;
          const t = typeof row.type === "string" ? row.type : "";
          if (t === "history" && Array.isArray(row.messages)) {
            const mapped: BallroomBubble[] = [];
            for (let i = 0; i < row.messages.length; i += 1) {
              const m = row.messages[i] as Record<string, unknown>;
              const agentRaw = typeof m.agent === "string" ? m.agent : "Agent";
              const textRaw = typeof m.text === "string" ? m.text : "";
              mapped.push({
                id: `hist-${i}`,
                agent: agentRaw,
                text: textRaw || String(m.type ?? ""),
                timestamp: typeof m.timestamp === "string" ? (m.timestamp as string) : new Date().toISOString(),
                variant: "agent",
              });
            }
            setMessages(mapped);
            return;
          }
          if (t === "ballroom.orchestrator_out") {
            const agent = typeof row.agent === "string" ? row.agent : "Orchestrator";
            const report = typeof row.text === "string" ? row.text : "";
            const voiceScript =
              typeof row.voice_script === "string" && row.voice_script.trim() ? String(row.voice_script) : report;
            appendBubble({
              agent,
              text: report,
              timestamp: new Date().toISOString(),
              variant: "agent",
            });
            if (typeof window !== "undefined" && "speechSynthesis" in window && !mutedRef.current) {
              window.speechSynthesis.cancel();
              const u = new SpeechSynthesisUtterance(voiceScript.slice(0, 2500));
              u.lang = "sk-SK";
              const voiceLabel =
                sessionAgentsRef.current.find(
                  (a) =>
                    /orchestrator|queen|manager/i.test(a.name) ||
                    /orchestrator|manager/i.test(a.role ?? ""),
                )?.name ?? agent;
              setSpeaking(voiceLabel);
              u.onend = () => setSpeaking(null);
              window.speechSynthesis.speak(u);
            }
            return;
          }
          if (t === "ballroom.transcript" || t === "message") {
            const agent = typeof row.agent === "string" ? row.agent : "bee";
            const text = typeof row.text === "string" ? row.text : "";
            appendBubble({
              agent,
              text,
              timestamp: new Date().toISOString(),
              variant: "agent",
            });
            const al = agent.toLowerCase();
            const rows = sessionAgentsRef.current;
            const matchSpeaker =
              rows.find((row) => {
                const nl = row.name.toLowerCase();
                const rl = (row.role ?? "").toLowerCase();
                if (!nl) {
                  return false;
                }
                return (
                  al.includes(nl) ||
                  nl.split(/\s+/).some((p) => p.length > 2 && al.includes(p)) ||
                  (!!rl && al.includes(rl))
                );
              })?.name ?? null;
            if (matchSpeaker) {
              setSpeaking(matchSpeaker);
              window.setTimeout(() => setSpeaking(null), 2200);
            }
            return;
          }
          if (t.startsWith("ballroom.") || typeof row.text === "string") {
            appendBubble({
              agent: typeof row.agent === "string" ? String(row.agent) : "System",
              text: typeof row.text === "string" ? String(row.text) : JSON.stringify(row),
              timestamp: new Date().toISOString(),
              variant: row.type === "ballroom.error" ? "system" : "agent",
            });
          }
          if (t === "ballroom.ready") {
            appendBubble({
              agent: "System",
              text: typeof row.text === "string" ? String(row.text) : "Ballroom ready.",
              timestamp: new Date().toISOString(),
              variant: "system",
            });
          }
        } catch {
          appendBubble({
            agent: "System",
            text: String(evt.data),
            timestamp: new Date().toISOString(),
            variant: "system",
          });
        }
      };

      ws.onerror = () => setError("Ballroom websocket error");

      ws.onclose = () => {
        setConnected(false);
        setSessionLabel(null);
        sessionIdRef.current = null;
      };

      (window as Window & { __qs_ballroom_ws?: WebSocket }).__qs_ballroom_ws?.close?.();
      (window as Window & { __qs_ballroom_ws?: WebSocket }).__qs_ballroom_ws = ws;
    },
    [appendBubble, wsUrlFromSessionCapsule],
  );

  const startSession = useCallback(async () => {
    setStarting(true);
    setError(null);
    try {
      let res = await fetch("/api/proxy/ballroom/start", { method: "POST", credentials: "include" });
      if (!res.ok) {
        res = await fetch("/api/proxy/ballroom/session", { method: "POST", credentials: "include" });
      }
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const body = (await res.json()) as SessionCapsule;
      setMessages([]);
      bindWebSocketToCapsule(body);
      appendBubble({
        agent: "System",
        text: "Hive ballroom channel opening…",
        timestamp: new Date().toISOString(),
        variant: "system",
      });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "session_failed");
      appendBubble({
        agent: "System",
        text: `Failed to start session (${exc instanceof Error ? exc.message : "unknown"})`,
        timestamp: new Date().toISOString(),
        variant: "system",
      });
    } finally {
      setStarting(false);
    }
  }, [appendBubble, bindWebSocketToCapsule]);

  const endSession = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
    sessionIdRef.current = null;
    setSessionLabel(null);
    appendBubble({
      agent: "System",
      text: "Session ended.",
      timestamp: new Date().toISOString(),
      variant: "system",
    });
  }, [appendBubble]);

  async function sendChat(): Promise<void> {
    const text = input.trim();
    if (!text) return;
    appendBubble({ agent: "You", text, timestamp: new Date().toISOString(), variant: "user" });
    setInput("");
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify({ type: "user_message", text, session_id: sessionIdRef.current }));
      } catch {
        /* server may ignore inbound text */
      }
    }
    try {
      await fetch("/api/proxy/ballroom/message", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionIdRef.current, text }),
      });
    } catch {
      /* optional route */
    }
  }

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const sid = new URLSearchParams(window.location.search).get("session");
    if (sid) {
      bindWebSocketToCapsule({ session_id: sid });
    }
    return () => (window as Window & { __qs_ballroom_ws?: WebSocket }).__qs_ballroom_ws?.close?.();
  }, [bindWebSocketToCapsule]);

  function timeStr(ts: string): string {
    try {
      return new Date(ts).toLocaleTimeString("sk-SK", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      return "";
    }
  }

  return (
    <div className="flex min-h-[calc(100dvh-7rem)] flex-col gap-[var(--qs-gap)] pb-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-[family-name:var(--font-poppins)] text-[22px] font-bold text-[var(--qs-text)]">Ballroom</h1>
          <p className="mt-0.5 text-[13px] text-[var(--qs-text-3)]">Voice + text session with the swarm</p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm border border-[color:var(--qs-border)] bg-transparent"
            style={{ borderColor: muted ? "var(--qs-red)" : "var(--qs-border)" }}
            onClick={() => setMuted((v) => !v)}
          >
            {muted ? (
              <>
                <MicOffIcon className="mr-1 inline h-3.5 w-3.5" /> Muted
              </>
            ) : (
              <>
                <MicIcon className="mr-1 inline h-3.5 w-3.5" /> Sound
              </>
            )}
          </button>
          {!connected ? (
            <button type="button" className="qs-btn qs-btn--primary" disabled={starting} onClick={() => void startSession()}>
              {starting ? "Connecting…" : "Start session"}
            </button>
          ) : (
            <button type="button" className="qs-btn qs-btn--danger" onClick={endSession}>
              End session
            </button>
          )}
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-1 items-start gap-[var(--qs-gap)] lg:grid-cols-[1fr_280px]">
        <section className="qs-card flex min-h-[420px] flex-col overflow-hidden rounded-[var(--qs-radius-lg)] p-0 lg:min-h-[560px]">
          <div className="hive-scrollbar flex flex-1 flex-col gap-3 overflow-y-auto p-[var(--qs-pad)]">
            {messages.length === 0 ? (
              <div className="flex flex-1 flex-col items-center justify-center py-16 text-center text-[var(--qs-text-3)]">
                <div className="mb-3 text-5xl opacity-80">🎙</div>
                <p className="text-sm">Start a session to talk with your swarm</p>
              </div>
            ) : (
              messages.map((msg) => {
                const accent =
                  msg.variant === "user"
                    ? "#FFB800"
                    : msg.variant === "system"
                      ? "#5a5a7a"
                      : accentForName(msg.agent);
                const isUser = msg.variant === "user";
                return (
                  <div key={msg.id} className={cn("flex gap-2.5", isUser && "flex-row-reverse")}>
                    <div
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[13px]"
                      style={{
                        background: `${accent}22`,
                        border: `1px solid ${accent}44`,
                      }}
                    >
                      {isUser ? "👤" : msg.variant === "system" ? "⚙️" : "🐝"}
                    </div>
                    <div className="min-w-0 max-w-[78%]">
                      <div className={cn("mb-1 flex items-baseline gap-1.5 text-[10px] font-mono", isUser && "flex-row-reverse")}>
                        <span className="font-bold" style={{ color: accent }}>
                          {msg.agent}
                        </span>
                        <span className="text-[#3a3a5a]">{timeStr(msg.timestamp)}</span>
                      </div>
                      <div
                        className={cn(
                          "rounded-xl border px-3 py-2 text-[13px] leading-snug text-[#cccce0]",
                          isUser ? "rounded-br-sm border-[#FFB800]/30 bg-[#FFB800]/[0.06]" : "rounded-bl-sm border-[var(--qs-border)] bg-[var(--qs-surface-2)]",
                        )}
                      >
                        <span className="whitespace-pre-wrap">{msg.text}</span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
            <div ref={bottomRef} />
          </div>
          <footer className="flex gap-2.5 border-t border-[var(--qs-border)] px-3 py-3 sm:px-[var(--qs-pad)]">
            <input
              value={input}
              disabled={!connected}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void sendChat();
                }
              }}
              placeholder={connected ? "Send message to the swarm…" : "Start a session first…"}
              className="qs-input flex-1 rounded-[var(--qs-radius-sm)]"
            />
            <button type="button" className="qs-btn qs-btn--primary shrink-0 px-4 disabled:opacity-40" disabled={!connected || !input.trim()} onClick={() => void sendChat()}>
              Send →
            </button>
          </footer>
        </section>

        <aside className="qs-card flex h-fit flex-col gap-3 self-start rounded-[var(--qs-radius-lg)]">
          <p className="text-[11px] uppercase tracking-[0.1em] text-[var(--qs-text-3)]">Participants</p>
          <ul className="flex flex-col gap-2.5">
            {sessionAgents.length === 0 ? (
              <li className="rounded-[10px] border border-dashed border-[var(--qs-border)] px-3 py-3 text-center font-mono text-[11px] text-[var(--qs-text-3)]">
                Loading agents from hive…
              </li>
            ) : (
              sessionAgents.map((row) => {
                const name = row.name;
                const color = accentForName(name);
                const isSpeaking = speaking === name;
                return (
                  <li
                    key={row.id ?? name}
                  className={cn(
                    "flex items-center gap-3 rounded-[10px] border px-3 py-2.5 transition",
                    isSpeaking ? "border-transparent" : "border-[var(--qs-border)] bg-transparent",
                  )}
                  style={
                    isSpeaking
                      ? ({
                          borderColor: `${color}66`,
                          background: `${color}12`,
                        } satisfies CSSProperties)
                      : undefined
                  }
                >
                  <div className="qs-mini-hex" style={{ background: `${color}24`, outline: isSpeaking ? `1px solid ${color}80` : "none", outlineOffset: "-1px" }}>
                    🐝
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] font-semibold" style={{ color: isSpeaking ? color : "var(--qs-text)" }}>
                      {name}
                    </p>
                    <p className="font-mono text-[10px] text-[var(--qs-text-3)]">
                      {isSpeaking ? "speaking…" : connected ? "listening" : "offline"}
                    </p>
                  </div>
                  {isSpeaking ? (
                    <div className="flex items-end gap-0.5">
                      {[2, 5, 8, 6, 4].map((h, i) => (
                        <span
                          key={i}
                          className="qs-pulse w-[3px] rounded-sm"
                          style={{
                            background: color,
                            height: `${h}px`,
                            animationDelay: `${i * 0.08}s`,
                          }}
                        />
                      ))}
                    </div>
                  ) : null}
                </li>
                );
              })
            )}
          </ul>
          {!connected ? (
            <p className="mt-auto text-center text-[11px] text-[var(--qs-text-3)]">Start a session to activate agents</p>
          ) : (
            <div className="mt-auto rounded-lg border border-[#00FF88]/20 bg-[#00FF88]/[0.06] px-3 py-2 text-center">
              <p className="font-mono text-[10px] text-[#00FF88]">● SESSION ACTIVE</p>
              {sessionLabel ? (
                <p className="mt-1 truncate font-mono text-[9px] text-[#3a3a5a]">{sessionLabel}</p>
              ) : null}
            </div>
          )}
          {error ? <p className="text-center font-mono text-xs text-[var(--qs-red)]">{error}</p> : null}
        </aside>
      </div>
    </div>
  );
}
