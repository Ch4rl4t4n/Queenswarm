"use client";

import { MicIcon, MicOffIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { NeonButton } from "@/components/ui/neon-button";
import { buildHiveWebsocketHref } from "@/lib/public-ws";
import { cn } from "@/lib/utils";

interface SessionCapsule {
  session_id: string;
  ws_url?: string;
  ws_url_path?: string;
}

const SPEAKERS = ["Queen", "Scout", "Eval", "Sim", "Action"] as const;

const HEX_COLORS: Record<(typeof SPEAKERS)[number], string> = {
  Queen: "#FFB800",
  Scout: "#00FFFF",
  Eval: "#00FF88",
  Sim: "#C084FC",
  Action: "#FF00AA",
};

interface TranscriptLine {
  agent?: string;
  text?: string;
  type?: string;
}

export function BallroomPanel() {
  const [connected, setConnected] = useState(false);
  const [sessionLabel, setSessionLabel] = useState<string | null>(null);
  const [lines, setLines] = useState<TranscriptLine[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [muted, setMuted] = useState(false);
  const mutedRef = useRef(false);
  const [speaking, setSpeaking] = useState<string | null>(null);

  useEffect(() => {
    mutedRef.current = muted;
  }, [muted]);

  const appendLine = useCallback((line: TranscriptLine) => {
    setLines((prev) => [...prev.slice(-200), line]);
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
      setSessionLabel(capsule.session_id);
      const wsUrl = wsUrlFromSessionCapsule(capsule);
      if (!wsUrl) {
        setError("ws_url_unavailable");
        return;
      }
      const ws = new WebSocket(wsUrl);
      ws.onopen = () => setConnected(true);
      ws.onmessage = (evt) => {
        try {
          const row = JSON.parse(evt.data as string) as Record<string, unknown>;
          const t = typeof row.type === "string" ? row.type : "";
          if (t === "history" && Array.isArray(row.messages)) {
            for (const m of row.messages) {
              const o = m as Record<string, unknown>;
              appendLine({
                type: String(o.type ?? "message"),
                agent: typeof o.agent === "string" ? o.agent : undefined,
                text: typeof o.text === "string" ? o.text : undefined,
              });
            }
            return;
          }
          if (t === "ballroom.orchestrator_out") {
            const agent = typeof row.agent === "string" ? row.agent : "Queen";
            const report = typeof row.text === "string" ? row.text : "";
            const voiceScript =
              typeof row.voice_script === "string" && row.voice_script.trim() ? String(row.voice_script) : report;
            appendLine({ type: t, agent, text: report });
            if (typeof window !== "undefined" && "speechSynthesis" in window && !mutedRef.current) {
              window.speechSynthesis.cancel();
              const u = new SpeechSynthesisUtterance(voiceScript.slice(0, 2500));
              u.lang = "sk-SK";
              u.rate = 1;
              setSpeaking("Queen");
              u.onend = () => setSpeaking(null);
              window.speechSynthesis.speak(u);
            }
            return;
          }
          if (t === "ballroom.transcript" || t === "message") {
            const agent = typeof row.agent === "string" ? row.agent : "bee";
            const text = typeof row.text === "string" ? row.text : "";
            appendLine({ type: t, agent, text });
            const matchSpeaker = SPEAKERS.find((s) => {
              const al = agent.toLowerCase();
              if (s === "Queen") return al.includes("queen") || al.includes("orchestrator");
              return al.includes(s.toLowerCase());
            });
            if (matchSpeaker) {
              setSpeaking(matchSpeaker);
              window.setTimeout(() => setSpeaking(null), 2200);
            }
            return;
          }
          if (t.startsWith("ballroom.") || typeof row.text === "string") {
            appendLine(row as TranscriptLine);
          }
        } catch {
          appendLine({ type: "parse_error", text: String(evt.data) });
        }
      };
      ws.onerror = () => setError("Ballroom websocket error");
      ws.onclose = () => setConnected(false);
      (window as Window & { __qs_ballroom_ws?: WebSocket }).__qs_ballroom_ws?.close?.();
      (window as Window & { __qs_ballroom_ws?: WebSocket }).__qs_ballroom_ws = ws;
    },
    [appendLine, wsUrlFromSessionCapsule],
  );

  const startSession = useCallback(async () => {
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
      bindWebSocketToCapsule(body);
      setLines([]);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "session_failed");
    }
  }, [bindWebSocketToCapsule]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const sid = new URLSearchParams(window.location.search).get("session");
    if (sid) {
      bindWebSocketToCapsule({ session_id: sid });
    }
  }, [bindWebSocketToCapsule]);

  useEffect(() => () => (window as Window & { __qs_ballroom_ws?: WebSocket }).__qs_ballroom_ws?.close?.(), []);

  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-cyan/20 bg-hive-card/95 p-6 shadow-[0_0_40px_rgb(255_184_0/0.08)] md:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-cyan/10 pb-5">
          <div>
            <p className="font-[family-name:var(--font-space-grotesk)] text-xs font-semibold uppercase tracking-[0.2em] text-cyan/80">
              Ballroom · live transcript
            </p>
            <h2 className="mt-1 font-[family-name:var(--font-space-grotesk)] text-xl font-semibold text-[#fafafa]">
              {sessionLabel ? `Session ${sessionLabel.slice(0, 8)}…` : "Pripoj sa na stream"}
            </h2>
            <p className="mt-2 font-[family-name:var(--font-inter)] text-sm text-zinc-500">
              Queen posiela finálny text a hlas po dokončení úlohy. Transcript sa doplňuje počas behu misie.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <NeonButton variant="ghost" type="button" className="text-xs uppercase" onClick={() => setMuted((v) => !v)}>
              {muted ? (
                <>
                  <MicOffIcon className="h-4 w-4" /> Zvuk zap.
                </>
              ) : (
                <>
                  <MicIcon className="h-4 w-4" /> Zvuk vyp.
                </>
              )}
            </NeonButton>
          </div>
        </div>

        {connected ? (
          <div className="my-8 flex flex-wrap justify-center gap-6">
            {SPEAKERS.map((name) => {
              const c = HEX_COLORS[name];
              const active = speaking === name;
              return (
                <div key={name} className="flex flex-col items-center gap-1">
                  <div
                    className={cn(
                      "hive-hex-clip-pointy flex h-16 w-14 items-center justify-center border-[6px] bg-[#0d0d2b] transition-transform",
                      active && "scale-110",
                    )}
                    style={{
                      borderColor: c,
                      boxShadow: active ? `0 0 20px ${c}66` : undefined,
                    }}
                  >
                    <span className="font-[family-name:var(--font-space-grotesk)] text-sm font-bold" style={{ color: c }}>
                      {name.slice(0, 1)}
                    </span>
                  </div>
                  <span
                    className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.14em]"
                    style={{ color: active ? c : "#52525b" }}
                  >
                    {name}
                  </span>
                </div>
              );
            })}
          </div>
        ) : null}

        <div className="rounded-2xl border border-cyan/15 bg-black/45 p-4">
          <p className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.24em] text-zinc-500">
            Live transcript
          </p>
          <ul className="mt-4 max-h-[50vh] overflow-y-auto divide-y divide-cyan/[0.06] font-[family-name:var(--font-inter)] text-sm">
            {lines.length === 0 ? (
              <li className="py-6 text-center text-zinc-500">
                Zatiaľ žiadne riadky. Spusti úlohu z dashboardu alebo pripoj novú session.
              </li>
            ) : (
              lines.map((ln, idx) => (
                <li key={`${String(idx)}-${ln.type ?? ln.agent ?? ""}`} className="py-3">
                  {ln.agent ? <span className="font-semibold text-pollen">{ln.agent}</span> : null}{" "}
                  <span className="whitespace-pre-wrap text-[#e4e4e7]">{ln.text ?? ln.type ?? "…"}</span>
                </li>
              ))
            )}
          </ul>
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 font-[family-name:var(--font-jetbrains-mono)] text-xs">
          <span className={connected ? "text-success" : "text-zinc-500"}>
            WebSocket: {connected ? "pripojené" : "odpojené"}
          </span>
          {error ? <span className="text-danger">{error}</span> : null}
          <NeonButton type="button" variant="primary" className="text-[10px] uppercase" onClick={() => void startSession()}>
            <MicIcon className="h-4 w-4" /> Nová session
          </NeonButton>
        </div>
      </section>
    </div>
  );
}
