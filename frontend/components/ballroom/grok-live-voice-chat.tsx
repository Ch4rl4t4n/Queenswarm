"use client";

import { Loader2, MicIcon, MicOffIcon } from "lucide-react";
import type { JSX } from "react";
import { useCallback, useEffect, useRef, useState } from "react";

import { HiveApiError, hivePostJson } from "@/lib/api";
import { cn } from "@/lib/utils";

const PCM_SAMPLE_RATE = 16_000;
const XAI_VOICES = ["eve", "ara", "rex", "sal", "leo"] as const;

interface GrokLiveVoiceButtonProps {
  readonly disabled?: boolean;
  readonly voiceId?: string;
  readonly sessionInstructions?: string;
  readonly onUserLine?: (text: string) => void;
  readonly onAssistantLine?: (text: string) => void;
  readonly onStatusChange?: (status: "idle" | "connecting" | "live" | "error") => void;
  readonly onError?: (message: string) => void;
  readonly className?: string;
}

interface LiveTokenResponse {
  ok?: boolean;
  client_secret?: string;
  ws_url?: string;
  model?: string;
  detail?: string;
}

function mapVoiceId(raw: string | undefined): string {
  const v = (raw ?? "eve").trim().toLowerCase();
  return (XAI_VOICES as readonly string[]).includes(v) ? v : "eve";
}

function downsampleTo16k(input: Float32Array, inputRate: number): Float32Array {
  if (inputRate === PCM_SAMPLE_RATE) {
    return input;
  }
  const ratio = inputRate / PCM_SAMPLE_RATE;
  const outLen = Math.max(1, Math.floor(input.length / ratio));
  const out = new Float32Array(outLen);
  for (let i = 0; i < outLen; i += 1) {
    out[i] = input[Math.floor(i * ratio)] ?? 0;
  }
  return out;
}

function float32ToBase64Pcm16(float32: Float32Array): string {
  const pcm16 = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i += 1) {
    const s = Math.max(-1, Math.min(1, float32[i] ?? 0));
    pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  const bytes = new Uint8Array(pcm16.buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i]!);
  }
  return btoa(binary);
}

function base64Pcm16ToFloat32(base64: string): Float32Array {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  const pcm16 = new Int16Array(bytes.buffer);
  const float32 = new Float32Array(pcm16.length);
  for (let i = 0; i < pcm16.length; i += 1) {
    float32[i] = pcm16[i]! / 32_768;
  }
  return float32;
}

function extractAssistantTranscriptFromResponseDone(event: Record<string, unknown>): string {
  const response = event.response;
  if (!response || typeof response !== "object") {
    return "";
  }
  const output = (response as { output?: unknown }).output;
  if (!Array.isArray(output)) {
    return "";
  }
  const parts: string[] = [];
  for (const item of output) {
    if (!item || typeof item !== "object") {
      continue;
    }
    const content = (item as { content?: unknown }).content;
    if (!Array.isArray(content)) {
      continue;
    }
    for (const part of content) {
      if (!part || typeof part !== "object") {
        continue;
      }
      const transcript = (part as { transcript?: unknown }).transcript;
      if (typeof transcript === "string" && transcript.trim()) {
        parts.push(transcript.trim());
      }
    }
  }
  return parts.join(" ").trim();
}

function readEventTranscript(event: Record<string, unknown>): string {
  if (typeof event.transcript === "string") {
    return event.transcript.trim();
  }
  const item = event.item;
  if (item && typeof item === "object" && typeof (item as { transcript?: string }).transcript === "string") {
    return (item as { transcript: string }).transcript.trim();
  }
  return "";
}

/** Compact mic toggle — live Grok voice streams into parent chat via callbacks. */
export function GrokLiveVoiceButton({
  disabled = false,
  voiceId,
  sessionInstructions,
  onUserLine,
  onAssistantLine,
  onStatusChange,
  onError,
  className,
}: GrokLiveVoiceButtonProps): JSX.Element {
  const [live, setLive] = useState(false);
  const [connecting, setConnecting] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const nextPlayTimeRef = useRef(0);
  const assistantBufferRef = useRef("");
  const assistantLineEmittedRef = useRef("");
  const userTranscriptRef = useRef("");
  const lastUserLineEmittedRef = useRef("");
  const liveRef = useRef(false);

  const reportError = useCallback(
    (message: string) => {
      onError?.(message);
      onStatusChange?.("error");
    },
    [onError, onStatusChange],
  );

  const emitAssistantLine = useCallback(
    (raw: string) => {
      const text = raw.trim();
      if (!text || text === assistantLineEmittedRef.current) {
        return;
      }
      assistantLineEmittedRef.current = text;
      onAssistantLine?.(text);
    },
    [onAssistantLine],
  );

  const emitUserLine = useCallback(
    (raw: string) => {
      const text = raw.trim();
      if (!text || text === lastUserLineEmittedRef.current) {
        return;
      }
      lastUserLineEmittedRef.current = text;
      onUserLine?.(text);
    },
    [onUserLine],
  );

  const cleanup = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    processorRef.current?.disconnect();
    processorRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    void audioCtxRef.current?.close();
    audioCtxRef.current = null;
    nextPlayTimeRef.current = 0;
    assistantBufferRef.current = "";
    assistantLineEmittedRef.current = "";
    userTranscriptRef.current = "";
    lastUserLineEmittedRef.current = "";
    liveRef.current = false;
    setLive(false);
    setConnecting(false);
    onStatusChange?.("idle");
  }, [onStatusChange]);

  useEffect(() => () => cleanup(), [cleanup]);

  const scheduleAudio = useCallback((float32: Float32Array) => {
    const ctx = audioCtxRef.current;
    if (!ctx || float32.length === 0) {
      return;
    }
    const buffer = ctx.createBuffer(1, float32.length, PCM_SAMPLE_RATE);
    const channel = new Float32Array(float32.length);
    channel.set(float32);
    buffer.copyToChannel(channel, 0);
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    const startAt = Math.max(ctx.currentTime, nextPlayTimeRef.current);
    source.start(startAt);
    nextPlayTimeRef.current = startAt + buffer.duration;
  }, []);

  const handleServerEvent = useCallback(
    (event: Record<string, unknown>) => {
      const t = typeof event.type === "string" ? event.type : "";

      if (t === "response.output_audio.delta") {
        const delta = typeof event.delta === "string" ? event.delta : "";
        if (delta) {
          scheduleAudio(base64Pcm16ToFloat32(delta));
        }
        return;
      }

      if (
        t === "response.output_audio_transcript.delta" ||
        t === "response.text.delta" ||
        t === "response.output_text.delta"
      ) {
        const delta = typeof event.delta === "string" ? event.delta : "";
        if (delta) {
          assistantBufferRef.current += delta;
        }
        return;
      }

      if (t === "response.output_audio_transcript.done") {
        const transcript = readEventTranscript(event) || assistantBufferRef.current.trim();
        if (transcript) {
          emitAssistantLine(transcript);
        }
        assistantBufferRef.current = "";
        return;
      }

      if (t === "response.done") {
        const fromBuffer = assistantBufferRef.current.trim();
        const fromPayload = extractAssistantTranscriptFromResponseDone(event);
        const full = fromBuffer || fromPayload;
        if (full) {
          emitAssistantLine(full);
        }
        assistantBufferRef.current = "";
        return;
      }

      if (t === "conversation.item.input_audio_transcription.completed") {
        const text = readEventTranscript(event);
        if (text) {
          userTranscriptRef.current = text;
        }
        return;
      }

      if (t === "input_audio_buffer.speech_stopped") {
        emitUserLine(userTranscriptRef.current);
        return;
      }

      if (t === "error") {
        const detail =
          typeof event.error === "object" && event.error !== null && "message" in event.error
            ? String((event.error as { message?: string }).message ?? "Voice session error")
            : "Voice session error";
        reportError(detail);
      }
    },
    [emitAssistantLine, emitUserLine, reportError, scheduleAudio],
  );

  const startLive = useCallback(async () => {
    if (disabled || live || connecting) {
      return;
    }
    setConnecting(true);
    onStatusChange?.("connecting");

    try {
      const tokenOut = await hivePostJson<LiveTokenResponse>("ballroom/voice/live-token", {});
      const secret = tokenOut.client_secret?.trim();
      const wsUrl = tokenOut.ws_url?.trim() || "wss://api.x.ai/v1/realtime?model=grok-voice-latest";
      if (!secret) {
        throw new Error("Voice token missing — check Grok API key in Settings.");
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioCtx = new AudioContext({ sampleRate: PCM_SAMPLE_RATE });
      await audioCtx.resume();
      const source = audioCtx.createMediaStreamSource(stream);
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      source.connect(processor);
      processor.connect(audioCtx.destination);

      const ws = new WebSocket(wsUrl, [`xai-client-secret.${secret}`]);
      wsRef.current = ws;
      streamRef.current = stream;
      audioCtxRef.current = audioCtx;
      processorRef.current = processor;

      ws.onopen = () => {
        ws.send(
          JSON.stringify({
            type: "session.update",
            session: {
              voice: mapVoiceId(voiceId),
              instructions:
                sessionInstructions?.trim() ||
                "You are the Queenswarm Orchestrator. Have a natural spoken conversation with the operator. " +
                  "Be concise, helpful, and direct. No markdown. Respond in the same language the user speaks.",
              turn_detection: { type: "server_vad" },
              audio: {
                input: { format: { type: "audio/pcm", rate: PCM_SAMPLE_RATE } },
                output: { format: { type: "audio/pcm", rate: PCM_SAMPLE_RATE } },
              },
            },
          }),
        );
        setLive(true);
        liveRef.current = true;
        setConnecting(false);
        onStatusChange?.("live");
      };

      ws.onmessage = (msg) => {
        try {
          const event = JSON.parse(String(msg.data)) as Record<string, unknown>;
          handleServerEvent(event);
        } catch {
          /* ignore malformed frames */
        }
      };

      ws.onerror = () => {
        reportError("Voice connection failed.");
        cleanup();
      };

      ws.onclose = () => {
        cleanup();
      };

      processor.onaudioprocess = (ev) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          return;
        }
        const input = ev.inputBuffer.getChannelData(0);
        const downsampled = downsampleTo16k(input, audioCtx.sampleRate);
        const encoded = float32ToBase64Pcm16(downsampled);
        wsRef.current.send(JSON.stringify({ type: "input_audio_buffer.append", audio: encoded }));
      };
    } catch (exc) {
      const detail =
        exc instanceof HiveApiError ? exc.message : exc instanceof Error ? exc.message : "Could not start voice call.";
      reportError(detail);
      cleanup();
    }
  }, [cleanup, connecting, disabled, handleServerEvent, live, onStatusChange, reportError, sessionInstructions, voiceId]);

  const toggleLive = useCallback(() => {
    if (live) {
      cleanup();
      return;
    }
    void startLive();
  }, [cleanup, live, startLive]);

  const label = connecting ? "Connecting voice…" : live ? "End voice call" : "Start voice call";

  return (
    <button
      type="button"
      className={cn(
        "qs-btn h-11 shrink-0 px-3",
        live ? "qs-btn--danger" : "qs-btn--ghost",
        connecting && "opacity-70",
        className,
      )}
      disabled={disabled || connecting}
      aria-label={label}
      aria-pressed={live}
      title={label}
      onClick={toggleLive}
    >
      {connecting ? (
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
      ) : live ? (
        <MicOffIcon className="h-4 w-4" aria-hidden />
      ) : (
        <MicIcon className="h-4 w-4" aria-hidden />
      )}
    </button>
  );
}

/** @deprecated Use GrokLiveVoiceButton — kept for import compatibility during rollout. */
export const GrokLiveVoiceChat = GrokLiveVoiceButton;
