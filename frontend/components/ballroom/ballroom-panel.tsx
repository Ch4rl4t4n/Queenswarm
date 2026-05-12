"use client";

import { MicIcon, MicOffIcon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { NeonButton } from "@/components/ui/neon-button";
import { buildHiveWebsocketHref } from "@/lib/public-ws";

interface SessionCapsule {
  session_id: string;
  ws_url?: string;
  ws_url_path?: string;
}

const SPEAKERS = ["Scout", "Eval", "Sim", "Action"] as const;

const HEX_COLORS: Record<(typeof SPEAKERS)[number], string> = {
  Scout: "#00FFFF",
  Eval: "#00FF88",
  Sim: "#FFB800",
  Action: "#FF00AA",
};
interface TranscriptLine {
  agent?: string;
  text?: string;
  type?: string;
}

const MOCK_AGENTS = [
  { name: "Queen", role: "Hive · coord", grad: "bg-gradient-to-br from-pollen to-[#FF6B9D]" },
  { name: "Eval-01", role: "Eval", grad: "bg-gradient-to-br from-pollen/90 to-amber-800" },
  { name: "Sim-01", role: "Sandbox", grad: "bg-gradient-to-br from-fuchsia-600 to-alert" },
  { name: "Scout-03", role: "Scout", grad: "bg-gradient-to-br from-cyan-400 to-data" },
  { name: "Action-07", role: "Trader", grad: "bg-gradient-to-br from-emerald-600 to-success" },
  { name: "Sim-02", role: "Stress", grad: "bg-gradient-to-br from-violet-600 to-data" },
  { name: "Eval-04", role: "Judge", grad: "bg-gradient-to-br from-amber-600 to-pollen" },
  { name: "Scout-01", role: "Feeds", grad: "bg-gradient-to-br from-sky-400 to-cyan-600" },
] as const;

const OTHER_ROOMS = [
  { title: "Recipe refinement · blog flow", meta: "BlogBot + Eval-03", time: "03:47" },
  { title: "Recipe library review", meta: "Chief + Sim-04", time: "06:12" },
] as const;

const MOCK_TRANSCRIPT = [
  { who: "Queen", role: "Hive", hue: "text-pollen", line: "Consensus: lean into macro tailwinds for ACKIE." },
  { who: "Eval-04", role: "Judge", hue: "text-pollen", line: "Confidence 0.78 on alt scenario — needs sim stress." },
  { who: "Sim-01", role: "Sandbox", hue: "text-alert", line: "Ran 6 permutations; max drawdown capped at 14%." },
] as const;

export function BallroomPanel() {
  const [connected, setConnected] = useState(false);
  const [lines, setLines] = useState<TranscriptLine[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [muted, setMuted] = useState(false);
  const [speaking, setSpeaking] = useState<string | null>(null);

  const appendLine = useCallback((line: TranscriptLine) => {
    setLines((prev) => [...prev.slice(-140), line]);
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
      const wsUrl = wsUrlFromSessionCapsule(body);
      if (!wsUrl) {
        throw new Error("ws_url_unavailable");
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
          if (t === "ballroom.transcript" || t === "message") {
            const agent = typeof row.agent === "string" ? row.agent : "bee";
            const text = typeof row.text === "string" ? row.text : "";
            appendLine({ type: t, agent, text });
            const matchSpeaker = SPEAKERS.find((s) => agent.toLowerCase().includes(s.toLowerCase()));
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
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "session_failed");
    }
  }, [appendLine, wsUrlFromSessionCapsule]);

  useEffect(() => () => (window as Window & { __qs_ballroom_ws?: WebSocket }).__qs_ballroom_ws?.close?.(), []);

  const feed = lines.length === 0 ? MOCK_TRANSCRIPT : null;

  return (
    <div className="space-y-10">
      <section className="rounded-3xl border border-alert/25 bg-hive-card/95 p-6 shadow-[0_0_52px_rgb(255_0_170/0.12)] md:p-8">
        <div className="flex flex-wrap items-start justify-between gap-6 border-b border-cyan/[0.08] pb-6">
          <div className="min-w-0 space-y-2">
            <p className="font-[family-name:var(--font-space-grotesk)] text-xs font-semibold uppercase tracking-[0.24em] text-alert">
              Active session · ACKIE capsule
            </p>
            <h2 className="font-[family-name:var(--font-space-grotesk)] text-2xl font-semibold tracking-tight text-[#fafafa]">
              Trading strategy review • ACKIE
            </h2>
            <div className="flex flex-wrap items-center gap-3 font-[family-name:var(--font-inter)] text-sm text-muted-foreground">
              <span className="inline-flex items-center gap-1 rounded-full border border-success/35 bg-success/[0.1] px-2 py-0.5 text-[11px] font-semibold text-success">
                ● Live
              </span>
              <span aria-hidden>|</span>
              <span>14:22</span>
              <span aria-hidden>|</span>
              <span>8 agents · 2 speaking</span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <NeonButton variant="ghost" type="button" className="text-xs uppercase" onClick={() => setMuted((v) => !v)}>
              {muted ? (
                <>
                  <MicOffIcon className="h-4 w-4" /> Unmute
                </>
              ) : (
                <>
                  <MicIcon className="h-4 w-4" /> Mute
                </>
              )}
            </NeonButton>
            <NeonButton variant="danger" type="button" className="text-xs uppercase">
              Leave
            </NeonButton>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-x-3 gap-y-8 py-8 md:gap-x-5 md:gap-y-10 xl:grid-cols-4">
          {MOCK_AGENTS.map((bee) => (
            <div key={bee.name} className="flex flex-col items-center gap-2 rounded-2xl border border-cyan/[0.08] bg-black/35 px-4 py-5">
              <div className={`h-[52px] w-[52px] rounded-full bg-hive-card ${bee.grad} ring-4 ring-black/70 shadow-[0_0_26px_rgb(0_255_255/0.15)]`} />
              <p className="font-[family-name:var(--font-inter)] font-semibold text-[#fafafa]">{bee.name}</p>
              <p className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.12em] text-zinc-500">
                {bee.role}
              </p>
              <div className="mt-3 flex gap-1" aria-hidden>
                {[34, 50, 24, 40, 62, 58, 72, 62].slice(0, 8).map((h, idx) => (
                  <span
                    key={`${bee.name}-${String(idx)}`}
                    style={{ height: `${h}px` }}
                    className="w-[3px] rounded-full bg-data/65"
                  />
                ))}
              </div>
            </div>
          ))}
        </div>

        {connected ? (
          <div className="mb-10 flex flex-wrap justify-center gap-6">
            {SPEAKERS.map((name) => {
              const c = HEX_COLORS[name];
              const active = speaking === name;
              return (
                <div key={name} className="flex flex-col items-center gap-1">
                  <div
                    className={`flex h-16 w-14 items-center justify-center transition-transform ${active ? "scale-110" : ""}`}
                    style={{
                      clipPath: "polygon(50% 0%,100% 25%,100% 75%,50% 100%,0% 75%,0% 25%)",
                      background: "#0d0d2b",
                      border: `2px solid ${c}`,
                      boxShadow: active ? `0 0 20px ${c}66` : "none",
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

        <div className="rounded-2xl border border-cyan/[0.1] bg-black/45 p-4">
          <p className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.28em] text-zinc-500">
            Live transcript
          </p>
          <ul className="mt-4 divide-y divide-cyan/[0.06] font-[family-name:var(--font-inter)] text-sm">
            {feed
              ? feed.map((row) => (
                  <li key={row.who} className="flex flex-wrap gap-4 py-3">
                    <span className={`w-32 shrink-0 font-semibold ${row.hue}`}>
                      {row.who}
                      <span className="mt-0.5 block font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-normal uppercase tracking-[0.15em] text-zinc-500">
                        {row.role}
                      </span>
                    </span>
                    <span className="text-[#e4e4e7]">{row.line}</span>
                  </li>
                ))
              : lines.map((ln, idx) => (
                  <li key={`${String(idx)}-${ln.type ?? ln.agent ?? ""}`} className="py-3">
                    {ln.agent ? <span className="font-semibold text-alert">{ln.agent}</span> : null}{" "}
                    <span className="text-[#e4e4e7]">{ln.text ?? ln.type ?? "…"}</span>
                  </li>
                ))}
          </ul>
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 font-[family-name:var(--font-jetbrains-mono)] text-xs">
          <span className={connected ? "text-success" : "text-danger"}>
            Bridge: {connected ? "webrtc_lane_ready" : "idle"}
          </span>
          {error ? <span className="text-danger">{error}</span> : null}
          <NeonButton type="button" variant="primary" className="text-[10px] uppercase" onClick={() => void startSession()}>
            <MicIcon className="h-4 w-4" /> Join ballroom stream
          </NeonButton>
        </div>
      </section>

      <section>
        <h3 className="font-[family-name:var(--font-space-grotesk)] text-lg text-[#fafafa]">Other rooms</h3>
        <ul className="mt-4 space-y-3">
          {OTHER_ROOMS.map((room) => (
            <li
              key={room.title}
              className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-cyan/[0.1] bg-hive-card/90 px-4 py-4"
            >
              <div>
                <p className="font-[family-name:var(--font-inter)] font-semibold text-[#fafafa]">{room.title}</p>
                <p className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-500">{room.meta}</p>
              </div>
              <div className="flex items-center gap-4">
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-sm text-data">{room.time}</span>
                <NeonButton type="button" variant="ghost" className="text-xs uppercase">
                  Join
                </NeonButton>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
