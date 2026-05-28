"use client";

import Link from "next/link";
import { ArrowUp, ChevronDown, MicIcon, MicOffIcon, X } from "lucide-react";
import type { CSSProperties } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { Filters, type ChatFilter } from "@/components/ballroom/filters";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { GrokLiveVoiceButton } from "@/components/ballroom/grok-live-voice-chat";
import { V4Badge, V4Card } from "@/components/ui/v4";
import { HiveApiError, hiveDelete, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import type { SupervisorSessionEventRow, SupervisorSessionRow } from "@/lib/hive-types";
import { resolveHiveBearerToken } from "@/lib/hive-bearer-token";
import { LinkifyText } from "@/lib/linkify-text";
import { buildHiveWebsocketHref } from "@/lib/public-ws";
import { integrationsTabHref } from "@/lib/integrations-routes";
import { hiveOverviewHref } from "@/lib/hive-home-route";
import { useCenterActiveInScrollRow } from "@/lib/hooks/use-center-active-in-scroll-row";
import { cn } from "@/lib/utils";
import { formatVoiceLiveError } from "@/lib/voice-live-errors";

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
  hive_tier?: string | null;
}

interface BallroomSessionListItem {
  session_id: string;
  started_at?: string | null;
  message_count?: number;
  status?: string | null;
  title?: string | null;
  preview?: string | null;
  pinned?: boolean;
}

interface VoiceProviderPreferences {
  stt_provider: "auto" | "grok" | "deepgram" | "openai";
  tts_provider: "auto" | "grok" | "elevenlabs" | "openai";
  latency_mode: "balanced" | "fast";
  vad_threshold: number;
  silence_duration_ms: number;
  tts_voice_id: string;
  tts_language: string;
  tts_tone: string;
}

interface VoiceAudioEvent {
  audio_base64?: string;
  content_type?: string;
  text?: string;
  agent?: string;
}

type VoiceChatMode = "swarm" | "orchestrator";

interface ActiveChatPrompt {
  filterId: string | null;
  label: string;
  text: string;
}

const VOICE_CHAT_MODE: VoiceChatMode = "orchestrator";

const AGENT_ACCENTS: Record<string, string> = {
  Orchestrator: "#FFB800",
  Scout: "#00E5FF",
  Eval: "#FFB800",
  Sim: "#FF00AA",
  Action: "#00FF88",
  Queen: "#FFB800",
  System: "#5a5a7a",
};

function historyTimeLabel(iso?: string | null): string {
  if (!iso) {
    return "";
  }
  const ms = Date.parse(iso);
  if (Number.isNaN(ms)) {
    return "";
  }
  const diffSec = Math.max(1, Math.floor((Date.now() - ms) / 1000));
  if (diffSec < 60) {
    return "now";
  }
  const mins = Math.floor(diffSec / 60);
  if (mins < 60) {
    return `${mins}m`;
  }
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) {
    return `${hrs}h`;
  }
  return `${Math.floor(hrs / 24)}d`;
}

function parseChatPromptRow(raw: unknown): ActiveChatPrompt | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const row = raw as Record<string, unknown>;
  const label = typeof row.label === "string" ? row.label.trim() : "";
  const text = typeof row.text === "string" ? row.text.trim() : "";
  if (!text) {
    return null;
  }
  return { filterId: null, label: label || "Assignment", text };
}

function isOrchestratorLike(a: SessionAgentRow): boolean {
  const tier = (a.hive_tier ?? "").toLowerCase();
  if (tier === "orchestrator") {
    return true;
  }
  const nl = a.name.toLowerCase();
  const rl = (a.role ?? "").toLowerCase();
  return nl.includes("orchestrat") || rl.includes("orchestrat") || rl.includes("queen");
}

function isManagerLike(a: SessionAgentRow): boolean {
  const tier = (a.hive_tier ?? "").toLowerCase();
  if (tier === "manager") {
    return true;
  }
  const nl = a.name.toLowerCase();
  const rl = (a.role ?? "").toLowerCase();
  return nl.includes("manager") || rl.includes("manager");
}

/** Orchestrator first, then managers, then alphabetical — no fixed participant list. */
function sortSessionParticipants(agents: SessionAgentRow[]): SessionAgentRow[] {
  return [...agents].sort((a, b) => {
    const aLead = isOrchestratorLike(a);
    const bLead = isOrchestratorLike(b);
    if (aLead && !bLead) return -1;
    if (!aLead && bLead) return 1;

    const aMgr = isManagerLike(a);
    const bMgr = isManagerLike(b);
    if (aMgr && !bMgr) return -1;
    if (!aMgr && bMgr) return 1;

    return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
  });
}

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

function participantGlyph(name: string, role?: string, hiveTier?: string | null): string {
  const n = name.toLowerCase();
  const rl = (role ?? "").toLowerCase();
  const tier = (hiveTier ?? "").toLowerCase();
  if (tier === "orchestrator" || n.includes("orchestr") || n.includes("queen")) return "👑";
  if (n.includes("scribe")) return "📜";
  if (n.includes("sentinel")) return "🛡";
  if (n.includes("forge")) return "⚒";
  if (n.includes("oracle")) return "🔮";
  if (rl.includes("scout")) return "🔭";
  return "🐝";
}

function messageAvatar(msg: BallroomBubble): string {
  if (msg.variant === "user") return "You";
  if (msg.variant === "system") return "⚙";
  const n = msg.agent.toLowerCase();
  if (n.includes("queen")) return "👑";
  if (n.includes("scribe")) return "📜";
  if (n.includes("sentinel")) return "🛡";
  return "🐝";
}

interface BallroomWsStatus {
  connected: boolean;
  error: string | null;
  sessionBound: boolean;
}

interface BallroomPanelProps {
  readonly showHeader?: boolean;
  readonly variant?: "default" | "v4";
  readonly onStatusChange?: (status: BallroomWsStatus) => void;
}

export function BallroomPanel({
  showHeader = true,
  variant = "default",
  onStatusChange,
}: BallroomPanelProps): JSX.Element {
  /** WebSocket OPEN — transcripts stream live. */
  const [connected, setConnected] = useState(false);
  /** Session id minted / known — REST chat works immediately even before WS opens. */
  const [sessionBound, setSessionBound] = useState(false);
  const [starting, setStarting] = useState(false);
  const [messages, setMessages] = useState<BallroomBubble[]>([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [muted, setMuted] = useState(false);
  const mutedRef = useRef(false);
  const [speaking, setSpeaking] = useState<string | null>(null);
  const [orchestratorThinking, setOrchestratorThinking] = useState(false);
  const [activeChatPrompt, setActiveChatPrompt] = useState<ActiveChatPrompt | null>(null);
  const voiceChatMode: VoiceChatMode = VOICE_CHAT_MODE;
  const [voicePrefs, setVoicePrefs] = useState<VoiceProviderPreferences>({
    stt_provider: "auto",
    tts_provider: "auto",
    latency_mode: "fast",
    vad_threshold: 0.35,
    silence_duration_ms: 450,
    tts_voice_id: "eve",
    tts_language: "auto",
    tts_tone: "none",
  });
  const wsRef = useRef<WebSocket | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const messageScrollRef = useRef<HTMLDivElement | null>(null);
  const bottomAnchorRef = useRef<HTMLDivElement | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const [supervisorReplayId, setSupervisorReplayId] = useState<string | null>(null);
  const productMissionKickoffRef = useRef(false);
  const [sessionLabel, setSessionLabel] = useState<string | null>(null);
  const historyTrackRef = useCenterActiveInScrollRow<HTMLDivElement>(sessionLabel ?? "");
  const readOnlyReplay = supervisorReplayId !== null;
  const [sessionAgents, setSessionAgents] = useState<SessionAgentRow[]>([]);
  const sessionAgentsRef = useRef<SessionAgentRow[]>([]);
  const [recentSessions, setRecentSessions] = useState<BallroomSessionListItem[]>([]);
  const [historyExpanded, setHistoryExpanded] = useState(false);
  const [quickPromptsOpen, setQuickPromptsOpen] = useState(false);
  const reconnectStreamRef = useRef<() => void>(() => {});

  useEffect(() => {
    mutedRef.current = muted;
  }, [muted]);

  useEffect(() => {
    onStatusChange?.({ connected, error, sessionBound });
  }, [connected, error, sessionBound, onStatusChange]);

  useEffect(() => {
    sessionAgentsRef.current = sessionAgents;
  }, [sessionAgents]);

  useEffect(() => {
    void hiveGet<VoiceProviderPreferences>("llm-keys/voice-preferences")
      .then((next) => {
        setVoicePrefs({
          stt_provider: next.stt_provider ?? "auto",
          tts_provider: next.tts_provider ?? "auto",
          latency_mode: next.latency_mode ?? "fast",
          vad_threshold: typeof next.vad_threshold === "number" ? next.vad_threshold : 0.35,
          silence_duration_ms: typeof next.silence_duration_ms === "number" ? next.silence_duration_ms : 450,
          tts_voice_id: typeof next.tts_voice_id === "string" ? next.tts_voice_id : "eve",
          tts_language: typeof next.tts_language === "string" ? next.tts_language : "auto",
          tts_tone: typeof next.tts_tone === "string" ? next.tts_tone : "none",
        });
      })
      .catch(() => {});
  }, []);

  const loadRecentSessions = useCallback(async () => {
    try {
      const data = await hiveGet<{ sessions?: BallroomSessionListItem[] }>("ballroom/sessions");
      const rows = Array.isArray(data.sessions) ? data.sessions : [];
      rows.sort((a, b) => {
        const ap = a.pinned ? 1 : 0;
        const bp = b.pinned ? 1 : 0;
        if (ap !== bp) {
          return bp - ap;
        }
        const at = a.started_at ? Date.parse(a.started_at) : 0;
        const bt = b.started_at ? Date.parse(b.started_at) : 0;
        return bt - at;
      });
      setRecentSessions(rows.slice(0, 24));
    } catch {
      setRecentSessions([]);
    }
  }, []);

  const pinSession = useCallback(
    async (sessionId: string, pinned: boolean) => {
      try {
        await hivePatchJson(`ballroom/session/${sessionId}/meta`, { pinned });
        await loadRecentSessions();
      } catch (exc) {
        const detail =
          exc instanceof HiveApiError ? exc.message : exc instanceof Error ? exc.message : "Could not pin session.";
        window.alert(detail);
      }
    },
    [loadRecentSessions],
  );

  const renameSession = useCallback(
    async (sessionId: string, currentTitle?: string | null) => {
      const next = window.prompt("Session title", (currentTitle ?? "").trim());
      if (next === null) {
        return;
      }
      try {
        await hivePatchJson(`ballroom/session/${sessionId}/meta`, { title: next.trim() });
        await loadRecentSessions();
      } catch (exc) {
        const detail =
          exc instanceof HiveApiError ? exc.message : exc instanceof Error ? exc.message : "Could not rename session.";
        window.alert(detail);
      }
    },
    [loadRecentSessions],
  );

  const deleteSessionFromHistory = useCallback(
    async (sessionId: string) => {
      if (!window.confirm("Delete this chat session from history?")) {
        return;
      }
      try {
        await hiveDelete(`ballroom/session/${sessionId}`);
        if (sessionIdRef.current === sessionId) {
          wsRef.current?.close();
          wsRef.current = null;
          setConnected(false);
          sessionIdRef.current = null;
          setSessionLabel(null);
          setSessionBound(false);
          setMessages([]);
          setActiveChatPrompt(null);
        }
        await loadRecentSessions();
      } catch (exc) {
        const detail =
          exc instanceof HiveApiError ? exc.message : exc instanceof Error ? exc.message : "Could not delete session.";
        window.alert(detail);
      }
    },
    [loadRecentSessions],
  );

  const clearAllHistory = useCallback(async () => {
    const ids = recentSessions.map((row) => row.session_id);
    if (ids.length === 0) {
      return;
    }
    if (!window.confirm(`Delete ALL ${ids.length} chat sessions from history? This cannot be undone.`)) {
      return;
    }
    const activeId = sessionIdRef.current;
    const results = await Promise.allSettled(
      ids.map((sid) => hiveDelete(`ballroom/session/${sid}`)),
    );
    const failed = results.filter((r) => r.status === "rejected").length;
    if (failed > 0) {
      window.alert(`${failed} of ${ids.length} sessions could not be deleted. Try again.`);
    }
    if (activeId && ids.includes(activeId)) {
      wsRef.current?.close();
      wsRef.current = null;
      setConnected(false);
      sessionIdRef.current = null;
      setSessionLabel(null);
      setSessionBound(false);
      setMessages([]);
    }
    setHistoryExpanded(false);
    await loadRecentSessions();
  }, [recentSessions, loadRecentSessions]);

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
          hive_tier: typeof (a as { hive_tier?: unknown }).hive_tier === "string"
            ? ((a as { hive_tier: string }).hive_tier)
            : null,
        }));
        const managers = normalized.filter((a) => {
          const nl = a.name.toLowerCase();
          const rl = (a.role ?? "").toLowerCase();
          const tier = (a.hive_tier ?? "").toLowerCase();
          return (
            tier === "manager" ||
            tier === "orchestrator" ||
            nl.includes("manager") ||
            nl.includes("orchestrator") ||
            rl.includes("manager") ||
            rl.includes("orchestrator")
          );
        });
        const pool = managers.length > 0 ? managers : normalized;
        setSessionAgents(sortSessionParticipants(pool).slice(0, 10));
      })
      .catch(() => {});
  }, []);

  const scrollChatToLatest = useCallback((behavior: ScrollBehavior = "smooth") => {
    const anchor = bottomAnchorRef.current;
    if (anchor) {
      anchor.scrollIntoView({ behavior, block: "end" });
      return;
    }
    const el = messageScrollRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior });
    }
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    }
    historyTrackRef.current?.scrollTo({ left: 0, top: 0, behavior: "auto" });
  }, [historyTrackRef]);

  useEffect(() => {
    if (messages.length === 0) {
      return;
    }
    const behavior: ScrollBehavior = messages.length <= 2 ? "auto" : "smooth";
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        scrollChatToLatest(behavior);
      });
    });
  }, [messages, scrollChatToLatest]);

  const appendBubble = useCallback((patch: Omit<BallroomBubble, "id">) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
    setMessages((prev) => [...prev.slice(-240), { ...patch, id }]);
  }, []);

  const onVoiceUserLine = useCallback(
    (text: string) => {
      appendBubble({ agent: "You", text, timestamp: new Date().toISOString(), variant: "user" });
    },
    [appendBubble],
  );

  const onVoiceAssistantLine = useCallback(
    (text: string) => {
      appendBubble({
        agent: "Orchestrator",
        text,
        timestamp: new Date().toISOString(),
        variant: "agent",
      });
    },
    [appendBubble],
  );

  const onVoiceError = useCallback(
    (message: string) => {
      const text = formatVoiceLiveError(message);
      appendBubble({
        agent: "System",
        text,
        timestamp: new Date().toISOString(),
        variant: "system",
      });
      if (text.includes("LLM keys") || text.includes("neplatný")) {
        void import("sonner").then(({ toast }) => {
          toast.error(text, {
            action: {
              label: "LLM keys",
              onClick: () => {
                window.location.assign("/settings/llm-keys");
              },
            },
            duration: 12_000,
          });
        });
      }
    },
    [appendBubble],
  );

  const orchestratorVoiceInstructions = useMemo(() => {
    const base =
      "You are the Queenswarm Orchestrator. Have a natural spoken conversation with the operator. " +
      "Be concise, helpful, and direct. No markdown. Respond in the same language the user speaks.";
    if (!activeChatPrompt?.text.trim()) {
      return base;
    }
    return (
      `${base}\n\n## Active session assignment (${activeChatPrompt.label})\n` +
      `Follow this brief for every reply until the operator changes it:\n${activeChatPrompt.text.trim()}`
    );
  }, [activeChatPrompt]);

  const applyChatPrompt = useCallback(
    async (filter: ChatFilter) => {
      const sid = sessionIdRef.current;
      if (!sid) {
        appendBubble({
          agent: "System",
          text: "Start a ballroom session before applying a quick prompt.",
          timestamp: new Date().toISOString(),
          variant: "system",
        });
        return;
      }
      try {
        await hivePostJson<{ chat_prompt?: { label?: string; text?: string } }>(
          `ballroom/session/${sid}/prompt`,
          { label: filter.label, text: filter.text },
        );
        setActiveChatPrompt({ filterId: filter.id, label: filter.label, text: filter.text });
      } catch (exc) {
        const detail =
          exc instanceof HiveApiError ? exc.message : exc instanceof Error ? exc.message : "Could not apply prompt.";
        appendBubble({
          agent: "System",
          text: detail,
          timestamp: new Date().toISOString(),
          variant: "system",
        });
      }
    },
    [appendBubble],
  );

  const clearChatPrompt = useCallback(async () => {
    const sid = sessionIdRef.current;
    if (!sid) {
      setActiveChatPrompt(null);
      return;
    }
    try {
      await hiveDelete(`ballroom/session/${sid}/prompt`);
      setActiveChatPrompt(null);
    } catch (exc) {
      const detail =
        exc instanceof HiveApiError ? exc.message : exc instanceof Error ? exc.message : "Could not clear prompt.";
      appendBubble({
        agent: "System",
        text: detail,
        timestamp: new Date().toISOString(),
        variant: "system",
      });
    }
  }, [appendBubble]);

  const wsUrlFromSessionCapsule = useCallback((capsule: SessionCapsule, bearerToken: string | null): string => {
    if (typeof window === "undefined") {
      return "";
    }

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
    if (bearerToken) {
      url.searchParams.set("token", bearerToken);
    }
    return url.toString();
  }, []);

  const bindWebSocketToCapsule = useCallback(
    (capsule: SessionCapsule) => {
      setError(null);
      sessionIdRef.current = capsule.session_id;
      setSessionLabel(capsule.session_id);
      setSessionBound(true);

      void (async () => {
        const guestAllowed = process.env.NEXT_PUBLIC_BALLROOM_GUEST_WS === "true";
        const bearerToken = guestAllowed ? null : await resolveHiveBearerToken();
        const wsUrl = wsUrlFromSessionCapsule(capsule, bearerToken);
        if (!wsUrl) {
          setSessionBound(false);
          setError("ws_url_unavailable");
          return;
        }

        wsRef.current?.close();
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;
        setConnected(false);

        let opened = false;
        ws.onopen = () => {
          opened = true;
          setConnected(true);
          setError(null);
        };

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
              const isYou = agentRaw.trim().toLowerCase() === "you";
              mapped.push({
                id: `hist-${i}`,
                agent: agentRaw,
                text: textRaw || String(m.type ?? ""),
                timestamp: typeof m.timestamp === "string" ? (m.timestamp as string) : new Date().toISOString(),
                variant: isYou ? "user" : "agent",
              });
            }
            setMessages(mapped);
            setActiveChatPrompt(parseChatPromptRow(row.chat_prompt));
            return;
          }
          if (t === "ballroom.prompt_applied") {
            const nextPrompt = parseChatPromptRow(row.chat_prompt);
            if (nextPrompt) {
              setActiveChatPrompt((prev) => ({
                ...nextPrompt,
                filterId: prev?.label === nextPrompt.label ? (prev.filterId ?? null) : null,
              }));
            }
            appendBubble({
              agent: "System",
              text: typeof row.text === "string" ? row.text : "Assignment applied.",
              timestamp: new Date().toISOString(),
              variant: "system",
            });
            return;
          }
          if (t === "ballroom.prompt_cleared") {
            setActiveChatPrompt(null);
            appendBubble({
              agent: "System",
              text: typeof row.text === "string" ? row.text : "Session assignment cleared.",
              timestamp: new Date().toISOString(),
              variant: "system",
            });
            return;
          }
          if (t === "ballroom.thinking") {
            setOrchestratorThinking(true);
            return;
          }
          if (t === "ballroom.orchestrator_out") {
            setOrchestratorThinking(false);
            const agent = typeof row.agent === "string" ? row.agent : "Orchestrator";
            const report = typeof row.text === "string" ? row.text : "";
            appendBubble({
              agent,
              text: report,
              timestamp: new Date().toISOString(),
              variant: "agent",
            });
            /* Server emits ballroom.voice_audio — avoid duplicate client-side TTS (latency + overlap). */
            return;
          }
          if (t === "ballroom.voice_audio") {
            const ev = row as VoiceAudioEvent;
            const blob = typeof ev.audio_base64 === "string" ? ev.audio_base64 : "";
            if (!blob || mutedRef.current) {
              return;
            }
            const contentType = typeof ev.content_type === "string" && ev.content_type.trim() ? ev.content_type : "audio/mpeg";
            const label = typeof ev.agent === "string" && ev.agent.trim() ? ev.agent : "Orchestrator";
            setSpeaking(label);
            if (audioRef.current) {
              audioRef.current.pause();
            }
            const player = new Audio(`data:${contentType};base64,${blob}`);
            audioRef.current = player;
            player.onended = () => setSpeaking(null);
            void player.play().catch(() => setSpeaking(null));
            return;
          }
          if (t === "ballroom.transcript" || t === "message") {
            const agent = typeof row.agent === "string" ? row.agent : "bee";
            const text = typeof row.text === "string" ? row.text : "";
            const isUser = agent.trim().toLowerCase() === "you";
            if (!isUser && /orchestrator/i.test(agent)) {
              setOrchestratorThinking(false);
            }
            appendBubble({
              agent,
              text,
              timestamp: new Date().toISOString(),
              variant: isUser ? "user" : "agent",
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
          if (t === "ballroom.error") {
            return;
          }
          if (t === "ballroom.ready") {
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
        } catch {
          appendBubble({
            agent: "System",
            text: String(evt.data),
            timestamp: new Date().toISOString(),
            variant: "system",
          });
        }
      };

      ws.onerror = () => {
        if (!opened) {
          setError("Ballroom websocket error");
        }
      };

      ws.onclose = (evt) => {
        setConnected(false);
        if (evt.code === 1008 && sessionIdRef.current) {
          void resolveHiveBearerToken().then((token) => {
            if (token) {
              reconnectStreamRef.current();
            }
          });
        }
      };

      (window as Window & { __qs_ballroom_ws?: WebSocket }).__qs_ballroom_ws?.close?.();
      (window as Window & { __qs_ballroom_ws?: WebSocket }).__qs_ballroom_ws = ws;
      })();
    },
    [appendBubble, wsUrlFromSessionCapsule],
  );

  const loadSupervisorReplay = useCallback(async (supervisorSessionId: string) => {
    setStarting(true);
    setError(null);
    wsRef.current?.close();
    wsRef.current = null;
    sessionIdRef.current = null;
    setConnected(false);
    setSupervisorReplayId(supervisorSessionId);
    setSessionBound(true);
    setSessionLabel(`Supervisor · S-${supervisorSessionId.replace(/-/g, "").slice(-4).toUpperCase()}`);
    setMessages([]);
    setInput("");
    setActiveChatPrompt(null);
    try {
      const [session, events] = await Promise.all([
        hiveGet<SupervisorSessionRow>(`agents/sessions/${encodeURIComponent(supervisorSessionId)}`),
        hiveGet<SupervisorSessionEventRow[]>(`agents/sessions/${encodeURIComponent(supervisorSessionId)}/events?limit=200`),
      ]);
      const mapped: BallroomBubble[] = [
        {
          id: "supervisor-replay-intro",
          agent: "System",
          text: `Read-only replay · ${session.status} · ${session.goal}`,
          timestamp: new Date().toISOString(),
          variant: "system",
        },
      ];
      for (const event of [...events].reverse()) {
        mapped.push({
          id: event.id,
          agent: event.event_type.replaceAll("_", " "),
          text: event.message,
          timestamp: event.occurred_at,
          variant: event.level === "error" ? "system" : "agent",
        });
      }
      for (const sub of session.sub_agents ?? []) {
        if (sub.last_output) {
          mapped.push({
            id: `sub-out-${sub.id}`,
            agent: `${sub.role} output`,
            text: sub.last_output,
            timestamp: sub.completed_at ?? sub.started_at ?? new Date().toISOString(),
            variant: "agent",
          });
        }
        if (sub.error_text) {
          mapped.push({
            id: `sub-err-${sub.id}`,
            agent: `${sub.role} error`,
            text: sub.error_text,
            timestamp: sub.completed_at ?? sub.started_at ?? new Date().toISOString(),
            variant: "system",
          });
        }
      }
      setMessages(mapped);
    } catch (exc) {
      const msg = exc instanceof HiveApiError ? exc.message : exc instanceof Error ? exc.message : "Replay failed";
      toast.error(msg);
      setSessionBound(false);
      setSupervisorReplayId(null);
    } finally {
      setStarting(false);
    }
  }, []);

  const startSession = useCallback(
    async (opts?: { quiet?: boolean }): Promise<boolean> => {
      setStarting(true);
      setError(null);
      setSupervisorReplayId(null);
      try {
        let res: Response | null = null;
        for (let attempt = 0; attempt < 3; attempt += 1) {
          res = await fetch("/api/proxy/ballroom/start", { method: "POST", credentials: "include" });
          if (!res.ok) {
            res = await fetch("/api/proxy/ballroom/session", { method: "POST", credentials: "include" });
          }
          if (res.ok) {
            break;
          }
          const retryable = res.status === 502 || res.status === 503 || res.status === 429;
          if (!retryable || attempt >= 2) {
            break;
          }
          await new Promise((resolve) => window.setTimeout(resolve, 1200 * (attempt + 1)));
        }
        if (!res?.ok) {
          const status = res?.status ?? 0;
          if (status === 401) {
            throw new Error("sign_in_required");
          }
          if (status === 429) {
            throw new Error("rate_limited");
          }
          if (status === 502 || status === 503) {
            throw new Error("backend_unavailable");
          }
          throw new Error(`HTTP ${status || "unknown"}`);
        }
        const body = (await res.json()) as SessionCapsule;
        setMessages([]);
        setInput("");
        setActiveChatPrompt(null);
        bindWebSocketToCapsule(body);
        void loadRecentSessions();
        if (typeof window !== "undefined") {
          const next = new URL(window.location.href);
          next.searchParams.set("session", body.session_id);
          window.history.replaceState({}, "", `${next.pathname}${next.search}${next.hash}`);
        }
        if (!opts?.quiet) {
          appendBubble({
            agent: "System",
            text: "Hive ballroom channel opening…",
            timestamp: new Date().toISOString(),
            variant: "system",
          });
        }
        return true;
      } catch (exc) {
        const code = exc instanceof Error ? exc.message : "session_failed";
        const userMessage =
          code === "sign_in_required"
            ? "Sign in again to start a ballroom session."
            : code === "rate_limited"
              ? "Rate limit — wait a few seconds and try Start session again."
              : code === "backend_unavailable"
                ? "Backend is restarting — try Start session again in a moment."
                : `Could not start session (${code}).`;
        toast.error(userMessage);
        if (!opts?.quiet) {
          appendBubble({
            agent: "System",
            text: userMessage,
            timestamp: new Date().toISOString(),
            variant: "system",
          });
        }
        return false;
      } finally {
        setStarting(false);
      }
    },
    [appendBubble, bindWebSocketToCapsule, loadRecentSessions],
  );

  const ensureBallroomSessionForVoice = useCallback(async (): Promise<boolean> => {
    if (sessionIdRef.current) {
      return true;
    }
    return startSession({ quiet: true });
  }, [startSession]);

  const endSession = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setConnected(false);
    setMessages([]);
    setInput("");
    setActiveChatPrompt(null);
    sessionIdRef.current = null;
    setSessionLabel(null);
    setSessionBound(false);
    setSupervisorReplayId(null);
    void loadRecentSessions();
    if (typeof window !== "undefined") {
      const u = new URL(window.location.href);
      if (u.searchParams.has("session")) {
        u.searchParams.delete("session");
        window.history.replaceState({}, "", `${u.pathname}${u.search}${u.hash}`);
      }
    }
  }, [loadRecentSessions]);

  const refreshChat = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setMessages([]);
    setInput("");
    setError(null);
    void startSession({ quiet: true });
  }, [startSession]);

  const openSessionFromHistory = useCallback(
    (sessionId: string) => {
      if (!sessionId.trim()) {
        return;
      }
      setMessages([]);
      bindWebSocketToCapsule({ session_id: sessionId });
      if (typeof window !== "undefined") {
        const next = new URL(window.location.href);
        next.searchParams.set("session", sessionId);
        window.history.replaceState({}, "", `${next.pathname}${next.search}${next.hash}`);
      }
    },
    [bindWebSocketToCapsule],
  );

  const reconnectStream = useCallback(() => {
    const sid = sessionIdRef.current;
    if (!sid) {
      return;
    }
    bindWebSocketToCapsule({
      session_id: sid,
    });
  }, [bindWebSocketToCapsule]);

  useEffect(() => {
    reconnectStreamRef.current = reconnectStream;
  }, [reconnectStream]);

  async function sendChat(): Promise<void> {
    const text = input.trim();
    if (!text) return;
    const sid = sessionIdRef.current;
    if (!sid) {
      appendBubble({
        agent: "System",
        text: "Session id missing — start the ballroom again.",
        timestamp: new Date().toISOString(),
        variant: "system",
      });
      return;
    }
    appendBubble({ agent: "You", text, timestamp: new Date().toISOString(), variant: "user" });
    setInput("");
    setOrchestratorThinking(true);
    try {
      await hivePostJson<{ ok?: boolean; session_id?: string }>("ballroom/message", {
        session_id: sid,
        text,
        mode: voiceChatMode,
        preferred_stt_provider: voicePrefs.stt_provider,
        preferred_tts_provider: voicePrefs.tts_provider,
        latency_mode: voicePrefs.latency_mode,
        tts_voice_id: voicePrefs.tts_voice_id,
        tts_language: voicePrefs.tts_language,
        tts_tone: voicePrefs.tts_tone,
      });
    } catch (exc) {
      const detail =
        exc instanceof HiveApiError
          ? `Message could not reach the swarm (HTTP ${exc.status}${exc.message ? `: ${exc.message}` : ""}).`
          : "Network error sending to ballroom — try again.";
      appendBubble({
        agent: "System",
        text: detail,
        timestamp: new Date().toISOString(),
        variant: "system",
      });
      setOrchestratorThinking(false);
    }
  }

  useEffect(() => {
    void loadRecentSessions();
    if (typeof window === "undefined") {
      return undefined;
    }
    const params = new URLSearchParams(window.location.search);
    const supervisorSid = params.get("supervisor_session");
    if (supervisorSid) {
      void loadSupervisorReplay(supervisorSid);
      return () => (window as Window & { __qs_ballroom_ws?: WebSocket }).__qs_ballroom_ws?.close?.();
    }
    const sid = params.get("session");
    if (sid) {
      bindWebSocketToCapsule({ session_id: sid });
      if (params.get("mission") === "product" && !productMissionKickoffRef.current) {
        productMissionKickoffRef.current = true;
        void (async () => {
          try {
            const { runPendingProductMission } = await import("@/lib/product-mission");
            toast.message("Product Mission beží — sleduj transcript…");
            await runPendingProductMission(sid);
          } catch (exc) {
            const msg = exc instanceof Error ? exc.message : "Product mission failed.";
            toast.error(msg);
          }
        })();
      }
    }
    return () => (window as Window & { __qs_ballroom_ws?: WebSocket }).__qs_ballroom_ws?.close?.();
  }, [bindWebSocketToCapsule, loadRecentSessions, loadSupervisorReplay]);

  function timeStr(ts: string): string {
    try {
      return new Date(ts).toLocaleTimeString("sk-SK", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      return "";
    }
  }

  const emptyLaneHint = useMemo(() => {
    if (!sessionBound && starting) {
      return "Opening ballroom channel…";
    }
    if (!sessionBound) {
      return "Click Voice Chat or Start session to begin.";
    }
    return "Messages and agent replies appear here — say hello below.";
  }, [sessionBound, starting]);

  const HISTORY_COLLAPSED_LIMIT = 9;
  const visibleRecentSessions = historyExpanded
    ? recentSessions
    : recentSessions.slice(0, HISTORY_COLLAPSED_LIMIT);
  const activeSessionTitle = useMemo(() => {
    const row = recentSessions.find((r) => r.session_id === sessionLabel);
    const clean = (row?.title ?? row?.preview ?? "").trim();
    return clean || "Ballroom session";
  }, [recentSessions, sessionLabel]);
  const sessionMetaLine = useMemo(() => {
    const agentCount = sessionAgents.length || 0;
    const msgCount = messages.length;
    const chatCost = (msgCount * 0.003).toFixed(2);
    const base = `${agentCount} agents present · ${msgCount} msgs · est. cost $${chatCost}`;
    return orchestratorThinking ? `${base} · Orchestrator thinking…` : base;
  }, [sessionAgents.length, messages.length, orchestratorThinking]);
  const participantsLiveCount = connected
    ? sessionAgents.length
    : sessionAgents.filter((row) => speaking === row.name).length;
  const toolbarButtonClass =
    "qs-btn qs-btn--ghost h-9 min-w-[132px] justify-center px-3 text-[12px] sm:h-10 sm:min-w-[148px] sm:px-4 sm:text-[13px]";
  const topRowClass = "flex flex-wrap items-center justify-end gap-3";
  const panelShellClass =
    "flex h-[min(62dvh,620px)] min-h-[340px] max-h-[620px] flex-col self-stretch overflow-hidden rounded-(--qs-radius-lg) lg:h-[min(64dvh,700px)] lg:min-h-[420px] lg:max-h-[700px]";
  const chatStatusLabel = error ? "WS ERROR" : connected ? "LIVE STREAM" : sessionBound ? "STREAM CONNECTING" : "IDLE";
  const participantsTopBubble = (
    <div className="flex min-w-[220px] max-w-full items-center gap-2 rounded-xl border border-(--qs-border) bg-(--qs-surface-2)/80 px-2 py-1.5">
      <div className="hive-scrollbar flex min-w-0 flex-1 items-center gap-1.5 overflow-x-auto">
        {sessionAgents.length === 0 ? (
          <span className="px-1 text-[10px] text-(--qs-text-3)">No participants</span>
        ) : (
          sessionAgents.map((row) => {
            const color = accentForName(row.name);
            const isSpeaking = speaking === row.name;
            return (
              <button
                key={`top-${row.id ?? row.name}`}
                type="button"
                title={row.name}
                className={cn(
                  "flex h-8 w-8 shrink-0 items-center justify-center rounded-md border",
                  isSpeaking ? "border-transparent" : "border-(--qs-border)",
                )}
                style={isSpeaking ? ({ borderColor: `${color}66`, background: `${color}12` } satisfies CSSProperties) : undefined}
              >
                <span className="text-[13px]">🐝</span>
              </button>
            );
          })
        )}
      </div>
      <span
        className={cn(
          "shrink-0 rounded-md border px-2 py-1 font-mono text-[10px]",
          error
            ? "border-(--qs-red)/35 bg-(--qs-red)/10 text-(--qs-red)"
            : connected
              ? "border-[#00FF88]/35 bg-[#00FF88]/10 text-[#00FF88]"
              : "border-(--qs-border) text-(--qs-text-3)",
        )}
      >
        {chatStatusLabel}
      </span>
    </div>
  );

  if (variant === "v4") {
    return (
      <div className="v4-chat-shell v4-chat-shell--v4 flex min-h-0 flex-1 flex-col gap-4 pb-2">
        <div className="v4-ballroom-mobile-stage flex min-h-0 flex-1 flex-col gap-4">
          <V4Card tight className="v4-chat-participants shrink-0">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex min-w-0 flex-wrap items-center gap-4">
                <span className="v4-label-kicker shrink-0">Participants</span>
                <div className="v4-participants">
                  {sessionAgents.length === 0 ? (
                    <span className="text-xs text-(--qs-text-3)">No participants</span>
                  ) : (
                    sessionAgents.map((row) => {
                      const isLive = connected || speaking === row.name;
                      return (
                        <div key={`v4-${row.id ?? row.name}`} className="v4-participant" title={row.name}>
                          {participantGlyph(row.name, row.role, row.hive_tier)}
                          {isLive ? <span className="v4-participant-live" aria-hidden /> : null}
                        </div>
                      );
                    })
                  )}
                </div>
                <span className="text-xs text-(--qs-text-3)">
                  {participantsLiveCount}/{Math.max(sessionAgents.length, 1)} live
                </span>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {connected ? <V4Badge tone="ok">LIVE</V4Badge> : null}
                <V4Badge tone={error ? "err" : connected ? "info" : "warn"}>
                  {error ? "WS error" : connected ? "WS connected" : sessionBound ? "WS connecting" : "WS idle"}
                </V4Badge>
              </div>
            </div>
          </V4Card>

          <section className="v4-chat-main flex min-h-0 flex-1 flex-col">
            <div className="v4-chat-header">
              <div className="flex w-full min-w-0 items-start justify-between gap-3">
                <div className="flex min-w-0 flex-1 items-center gap-3">
                  <div className="v4-msg-avatar">🐝</div>
                  <div className="min-w-0">
                    <p className="truncate text-base font-semibold text-(--qs-text)">{activeSessionTitle}</p>
                    <p className="text-xs text-(--qs-text-3)">{sessionMetaLine}</p>
                  </div>
                </div>
                <HiveRefreshButton label="Refresh chat" onClick={refreshChat} />
              </div>
              <div className="v4-ballroom-session-toolbar">
                <div className="v4-ballroom-session-toolbar__left">
                  <Link href={integrationsTabHref("active", "ecosystem")} className="qs-btn qs-btn--ghost qs-btn--sm">
                    Ecosystem hub
                  </Link>
                  <Link href="/agents#sessions" className="qs-btn qs-btn--ghost qs-btn--sm">
                    Supervisor sessions
                  </Link>
                  {sessionBound && !connected ? (
                    <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => reconnectStream()}>
                      Reconnect
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className={cn("qs-btn qs-btn--ghost qs-btn--sm gap-1", muted && "text-(--qs-red)")}
                    onClick={() => setMuted((v) => !v)}
                  >
                    {muted ? <MicOffIcon className="h-3.5 w-3.5" aria-hidden /> : <MicIcon className="h-3.5 w-3.5" aria-hidden />}
                    {muted ? "Muted" : "Sound"}
                  </button>
                </div>
                <div className="v4-ballroom-session-toolbar__right">
                  {sessionBound && messages.length > 0 ? (
                    <Link
                      href={`${hiveOverviewHref()}?ballroom_session=${encodeURIComponent(sessionLabel ?? "")}#dialogue-extract`}
                      className="qs-btn qs-btn--ghost qs-btn--sm"
                    >
                      Dialogue Extract
                    </Link>
                  ) : null}
                  {!sessionBound ? (
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm"
                      disabled={starting}
                      onClick={() => void startSession()}
                    >
                      {starting ? "Connecting…" : "Start session"}
                    </button>
                  ) : (
                    <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm gap-1" onClick={endSession}>
                      <X className="h-3.5 w-3.5" aria-hidden />
                      End session
                    </button>
                  )}
                </div>
              </div>
            </div>

            <div ref={messageScrollRef} className="v4-chat-body hive-scrollbar">
              {messages.length === 0 ? (
                <div className="flex flex-1 flex-col items-center justify-center py-16 text-center text-(--qs-text-3)">
                  <div className="mb-3 text-5xl opacity-80">🎙</div>
                  <p className="text-sm">{emptyLaneHint}</p>
                </div>
              ) : (
                messages.map((msg) => {
                  const isUser = msg.variant === "user";
                  return (
                    <div key={msg.id} className={cn("v4-msg", isUser && "v4-msg--me")}>
                      <div className="v4-msg-avatar">{messageAvatar(msg)}</div>
                      <div className="min-w-0 max-w-[78%]">
                        <div className={cn("v4-msg-meta", isUser && "v4-msg-meta--me")}>
                          <span className="v4-msg-who">{isUser ? "You" : msg.agent}</span>
                          <span>{timeStr(msg.timestamp)}</span>
                        </div>
                        <div className={cn("v4-msg-bubble", isUser && "v4-msg-bubble--me")}>
                          <LinkifyText text={msg.text} className="whitespace-pre-wrap" />
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={bottomAnchorRef} className="h-px w-full shrink-0" aria-hidden />
            </div>

            <div className="v4-chat-filters">
              <button
                type="button"
                className="v4-ballroom-quick-prompt-toggle"
                aria-expanded={quickPromptsOpen}
                aria-controls="ballroom-quick-prompts-panel"
                onClick={() => setQuickPromptsOpen((open) => !open)}
              >
                <span className="min-w-0 truncate">
                  Quick prompt
                  {activeChatPrompt ? (
                    <span className="ml-1 font-normal text-(--qs-amber)">· {activeChatPrompt.label}</span>
                  ) : null}
                </span>
                <ChevronDown
                  className={cn("h-4 w-4 shrink-0 text-(--qs-text-3) transition", quickPromptsOpen && "rotate-180")}
                  aria-hidden
                />
              </button>
              {quickPromptsOpen ? (
                <div id="ballroom-quick-prompts-panel" className="v4-ballroom-quick-prompt-panel">
                  <p className="mb-2 text-[10px] uppercase tracking-[0.14em] text-(--qs-text-3)">
                    Session assignment · quick prompts
                  </p>
                  <Filters
                    disabled={!sessionBound || starting || readOnlyReplay}
                    variant="v4"
                    activePromptId={activeChatPrompt?.filterId ?? null}
                    activePromptLabel={activeChatPrompt?.label ?? null}
                    onActivatePrompt={(filter) => void applyChatPrompt(filter)}
                    onClearPrompt={() => void clearChatPrompt()}
                  />
                </div>
              ) : null}
            </div>

            <div className="v4-chat-composer">
              <div className="v4-chat-input-row v4-chat-input-row--text">
                <input
                  value={input}
                  disabled={!sessionBound || starting || readOnlyReplay}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void sendChat();
                    }
                  }}
                  placeholder={
                    readOnlyReplay
                      ? "Read-only supervisor replay — start a live session to chat"
                      : starting
                      ? "Opening channel…"
                      : sessionBound
                        ? "Message Orchestrator…"
                        : "Click Voice Chat or Start session…"
                  }
                  className="qs-input h-11 min-w-0 flex-1 rounded-(--qs-radius-sm)"
                />
                <button
                  type="button"
                  className="v4-ballroom-send-btn qs-btn qs-btn--primary h-11 w-11 shrink-0 p-0 disabled:opacity-40"
                  disabled={!sessionBound || starting || readOnlyReplay || !input.trim()}
                  aria-label="Send message"
                  onClick={() => void sendChat()}
                >
                  <ArrowUp className="v4-ballroom-send-icon" strokeWidth={2.5} aria-hidden />
                </button>
              </div>
              <div className="v4-chat-input-row v4-chat-input-row--voice">
                <GrokLiveVoiceButton
                  disabled={starting || readOnlyReplay}
                  layout="bar"
                  voiceId={voicePrefs.tts_voice_id}
                  sessionInstructions={orchestratorVoiceInstructions}
                  onBeforeStart={ensureBallroomSessionForVoice}
                  onUserLine={onVoiceUserLine}
                  onAssistantLine={onVoiceAssistantLine}
                  onError={onVoiceError}
                />
              </div>
            </div>
          </section>
        </div>

        <aside className="v4-chat-side shrink-0">
          <div className="flex items-center justify-between gap-2">
            <span className="v4-label-kicker">Chat history · {recentSessions.length}</span>
            {recentSessions.length > 0 ? (
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm shrink-0"
                onClick={() => void clearAllHistory()}
              >
                Clear all
              </button>
            ) : null}
          </div>
          <div ref={historyTrackRef} className="v4-chat-history-track hive-scrollbar">
            {recentSessions.length === 0 ? (
              <p className="py-3 text-center text-xs text-(--qs-text-3)">No recent sessions yet.</p>
            ) : (
              visibleRecentSessions.map((row) => {
                const active = sessionLabel === row.session_id;
                const title = (row.title ?? row.preview ?? "").trim() || "Untitled session";
                const when = historyTimeLabel(row.started_at);
                return (
                  <div
                    key={row.session_id}
                    data-subtab-active={active ? "true" : undefined}
                    className={cn("v4-chat-history-item", active && "v4-chat-history-item--active")}
                  >
                    <button
                      type="button"
                      className="w-full text-left"
                      onClick={() => openSessionFromHistory(row.session_id)}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <p className="truncate text-sm font-medium text-(--qs-text)">{title}</p>
                        {when ? <span className="shrink-0 text-[10px] text-(--qs-text-3)">{when}</span> : null}
                      </div>
                    </button>
                    {active ? (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        <button
                          type="button"
                          className={cn(
                            "rounded border px-2 py-0.5 text-[10px] transition",
                            row.pinned
                              ? "border-(--qs-amber)/45 bg-(--qs-amber)/12 text-(--qs-amber)"
                              : "border-(--qs-border) text-(--qs-text-3) hover:text-(--qs-cyan)",
                          )}
                          onClick={(e) => {
                            e.stopPropagation();
                            void pinSession(row.session_id, !row.pinned);
                          }}
                        >
                          {row.pinned ? "★ Pinned" : "☆ Pin"}
                        </button>
                        <button
                          type="button"
                          className="rounded border border-(--qs-border) px-2 py-0.5 text-[10px] text-(--qs-text-3) transition hover:text-(--qs-cyan)"
                          onClick={(e) => {
                            e.stopPropagation();
                            void renameSession(row.session_id, row.title);
                          }}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="rounded border border-(--qs-red)/45 px-2 py-0.5 text-[10px] text-(--qs-red) transition hover:bg-(--qs-red)/10"
                          onClick={(e) => {
                            e.stopPropagation();
                            void deleteSessionFromHistory(row.session_id);
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    ) : null}
                  </div>
                );
              })
            )}
          </div>
        </aside>
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-col gap-(--qs-gap) pb-2">
      {showHeader ? (
        <header className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="font-(family-name:--font-poppins) text-[22px] font-bold text-(--qs-text)">Ballroom</h1>
            <p className="mt-0.5 text-[13px] text-(--qs-text-3)">Voice + text session with the swarm</p>
          </div>
          <div className={topRowClass}>
            <Link href={integrationsTabHref("active", "ecosystem")} className={toolbarButtonClass}>
              Ecosystem hub
            </Link>
            <button
              type="button"
              className={cn(
                toolbarButtonClass,
                muted && "!border-(--qs-red) !text-(--qs-red)",
              )}
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
            {sessionBound && !connected ? (
              <button type="button" className={toolbarButtonClass} onClick={() => reconnectStream()}>
                Reconnect stream
              </button>
            ) : null}
            <HiveRefreshButton className={toolbarButtonClass} label="Refresh chat" onClick={refreshChat} />
            {!sessionBound ? (
              <button type="button" className={toolbarButtonClass} disabled={starting} onClick={() => void startSession()}>
                {starting ? "Connecting…" : "Start session"}
              </button>
            ) : (
              <button type="button" className={toolbarButtonClass} onClick={endSession}>
                End session
              </button>
            )}
            {participantsTopBubble}
          </div>
        </header>
      ) : (
        <div className={topRowClass}>
          <Link href={integrationsTabHref("active", "ecosystem")} className={toolbarButtonClass}>
            Ecosystem hub
          </Link>
          <button
            type="button"
            className={cn(
              toolbarButtonClass,
              muted && "!border-(--qs-red) !text-(--qs-red)",
            )}
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
          {sessionBound && !connected ? (
            <button type="button" className={toolbarButtonClass} onClick={() => reconnectStream()}>
              Reconnect stream
            </button>
          ) : null}
          <HiveRefreshButton className={toolbarButtonClass} label="Refresh chat" onClick={refreshChat} />
          {!sessionBound ? (
            <button type="button" className={toolbarButtonClass} disabled={starting} onClick={() => void startSession()}>
              {starting ? "Connecting…" : "Start session"}
            </button>
          ) : (
            <button type="button" className={toolbarButtonClass} onClick={endSession}>
              End session
            </button>
          )}
          {participantsTopBubble}
        </div>
      )}

      <div className="grid min-h-0 flex-1 grid-cols-1 items-stretch gap-3 lg:grid-cols-[minmax(0,260px)_minmax(0,1fr)] [&>.qs-card]:mt-0!">
        <aside className={cn("qs-card order-2 p-0 lg:order-1", panelShellClass)}>
          <div className="flex items-center justify-center border-b border-(--qs-border) px-3 py-3">
            <p className="text-center text-[11px] uppercase tracking-widest text-(--qs-text-3)">Chat history</p>
          </div>
          {historyExpanded && recentSessions.length > 0 ? (
            <div className="border-b border-(--qs-border) px-2 py-3">
              <button
                type="button"
                className="w-full rounded-md border border-(--qs-red)/45 bg-(--qs-red)/5 px-3 py-2 text-center text-[12px] font-semibold text-(--qs-red) transition hover:bg-(--qs-red)/15"
                onClick={() => void clearAllHistory()}
              >
                🗑 Clear all history ({recentSessions.length})
              </button>
            </div>
          ) : null}
          <div ref={historyTrackRef} className="v4-chat-history-track hive-scrollbar px-2 py-3">
            {recentSessions.length === 0 ? (
              <p className="px-2 py-3 text-center text-[11px] text-(--qs-text-3)">No recent sessions yet.</p>
            ) : (
              visibleRecentSessions.map((row) => {
                const active = sessionLabel === row.session_id;
                const cleanTitle = (row.title ?? "").trim();
                const cleanPreview = (row.preview ?? "").trim();
                const title = cleanTitle || cleanPreview || "Untitled session";
                const when = historyTimeLabel(row.started_at);
                return (
                  <div
                    key={row.session_id}
                    data-subtab-active={active ? "true" : undefined}
                    className={cn(
                      "rounded-md border px-3 py-2.5 text-left transition",
                      active
                        ? "border-(--qs-cyan)/45 bg-(--qs-cyan)/10"
                        : "border-(--qs-border) bg-(--qs-surface-2) hover:border-(--qs-cyan)/35",
                    )}
                  >
                    <button type="button" className="w-full text-left" onClick={() => openSessionFromHistory(row.session_id)}>
                      <div className="flex items-center justify-between gap-2">
                        <p className="truncate text-[14px] font-semibold text-(--qs-text)">{title}</p>
                        {when ? <p className="shrink-0 text-[12px] text-(--qs-text-3)">{when}</p> : null}
                      </div>
                    </button>
                    {active ? (
                    <div className="mt-3 flex items-center gap-2">
                      <button
                        type="button"
                        className={cn(
                          "rounded border px-1.5 py-0.5 text-[10px] transition",
                          row.pinned
                            ? "border-[#FFB800]/45 bg-[#FFB800]/12 text-[#FFB800]"
                            : "border-(--qs-border) text-(--qs-text-3) hover:text-(--qs-cyan)",
                        )}
                        onClick={(e) => {
                          e.stopPropagation();
                          void pinSession(row.session_id, !row.pinned);
                        }}
                      >
                        {row.pinned ? "★ Pinned" : "☆ Pin"}
                      </button>
                      <button
                        type="button"
                        className="rounded border border-(--qs-border) px-1.5 py-0.5 text-[10px] text-(--qs-text-3) transition hover:text-(--qs-cyan)"
                        onClick={(e) => {
                          e.stopPropagation();
                          void renameSession(row.session_id, row.title);
                        }}
                      >
                        Rename
                      </button>
                      <button
                        type="button"
                        className="rounded border border-(--qs-red)/45 px-1.5 py-0.5 text-[10px] text-(--qs-red) transition hover:bg-(--qs-red)/10"
                        onClick={(e) => {
                          e.stopPropagation();
                          void deleteSessionFromHistory(row.session_id);
                        }}
                      >
                        Delete
                      </button>
                    </div>
                    ) : null}
                  </div>
                );
              })
            )}
          </div>
          <div className="border-t border-(--qs-border) px-2 py-3">
            <button
              type="button"
              disabled={recentSessions.length <= HISTORY_COLLAPSED_LIMIT}
              className="w-full rounded-md border border-(--qs-border) bg-(--qs-surface-2) px-3 py-2 text-center text-[12px] font-semibold text-(--qs-text-3) transition hover:border-(--qs-cyan)/45 hover:text-(--qs-cyan) disabled:cursor-not-allowed disabled:opacity-50"
              onClick={() => setHistoryExpanded((v) => !v)}
            >
              {recentSessions.length <= HISTORY_COLLAPSED_LIMIT
                ? `Chat History (${recentSessions.length})`
                : historyExpanded
                  ? "Hide older chats"
                  : `Chat History (${recentSessions.length})`}
            </button>
          </div>
        </aside>

        <section className={cn("qs-card order-1 mt-0! p-0 lg:order-2", panelShellClass)}>
          <div ref={messageScrollRef} className="hive-scrollbar flex flex-1 flex-col gap-3 overflow-y-auto p-3">
            {messages.length === 0 ? (
              <div className="flex flex-1 flex-col items-center justify-center py-16 text-center text-(--qs-text-3)">
                <div className="mb-3 text-5xl opacity-80">🎙</div>
                <p className="text-sm">{emptyLaneHint}</p>
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
                          isUser ? "rounded-br-sm border-[#FFB800]/30 bg-[#FFB800]/[0.06]" : "rounded-bl-sm border-(--qs-border) bg-(--qs-surface-2)",
                        )}
                      >
                        <LinkifyText text={msg.text} className="whitespace-pre-wrap" />
                      </div>
                    </div>
                  </div>
                );
              })
            )}
            <div ref={bottomAnchorRef} className="h-px w-full shrink-0" aria-hidden />
          </div>
          <footer className="flex items-end gap-2.5 border-t border-(--qs-border) px-3 py-3 sm:px-(--qs-pad)">
            <div className="flex min-w-0 flex-1 flex-col gap-2">
              <Filters
                disabled={!sessionBound || starting || readOnlyReplay}
                activePromptId={activeChatPrompt?.filterId ?? null}
                activePromptLabel={activeChatPrompt?.label ?? null}
                onActivatePrompt={(filter) => void applyChatPrompt(filter)}
                onClearPrompt={() => void clearChatPrompt()}
              />
              <input
                value={input}
                disabled={!sessionBound || starting || readOnlyReplay}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void sendChat();
                  }
                }}
                placeholder={
                  readOnlyReplay
                    ? "Read-only supervisor replay — start a live session to chat"
                    : starting ? "Opening channel…"
                    : sessionBound ? "Message Orchestrator…"
                    : "Click Voice Chat or Start session…"
                }
                className="qs-input h-11 flex-1 rounded-(--qs-radius-sm)"
              />
            </div>
            <GrokLiveVoiceButton
              disabled={starting || readOnlyReplay}
              voiceId={voicePrefs.tts_voice_id}
              sessionInstructions={orchestratorVoiceInstructions}
              onBeforeStart={ensureBallroomSessionForVoice}
              onUserLine={onVoiceUserLine}
              onAssistantLine={onVoiceAssistantLine}
              onError={onVoiceError}
            />
            <button
              type="button"
              className="qs-btn qs-btn--primary h-11 shrink-0 px-4 disabled:opacity-40"
              disabled={!sessionBound || starting || readOnlyReplay || !input.trim()}
              onClick={() => void sendChat()}
            >
              Send →
            </button>
          </footer>
        </section>

      </div>
    </div>
  );
}
