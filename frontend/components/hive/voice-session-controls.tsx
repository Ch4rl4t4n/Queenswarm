"use client";

import type { JSX } from "react";
import { forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState } from "react";

import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { cn } from "@/lib/utils";

interface VoiceSessionControlsProps {
  readonly sessionId?: string | null;
  readonly dispatchToAgents?: boolean;
  readonly targetMode?: "swarm" | "orchestrator";
  readonly wsVoiceSend?: (payload: VoiceWsChunkPayload) => boolean;
  readonly allowBrowserFallback?: boolean;
  readonly preferredSttProvider?: "auto" | "grok" | "deepgram" | "openai";
  readonly preferredTtsProvider?: "auto" | "grok" | "elevenlabs" | "openai";
  readonly latencyMode?: "balanced" | "fast";
  readonly vadThreshold?: number;
  readonly silenceDurationMs?: number;
  readonly ttsVoiceId?: string;
  readonly ttsLanguage?: string;
  readonly ttsTone?: string;
  readonly disabled?: boolean;
  readonly compact?: boolean;
  readonly className?: string;
  readonly remoteTranscript?: string | null;
  readonly remoteError?: string | null;
  readonly onTranscript?: (text: string) => void;
  readonly onRecordingChange?: (recording: boolean) => void;
  readonly onRecordingSeconds?: (seconds: number) => void;
  readonly maxRecordingSeconds?: number;
  readonly onRecordingLimitReached?: () => void;
  readonly label?: string;
}

export interface VoiceSessionControlsHandle {
  toggleRecording: () => void;
  isRecording: () => boolean;
}

interface VoiceTranscribeResponse {
  text?: string;
  skipped?: boolean;
  detail?: string;
}

interface VoiceCapabilitiesResponse {
  ok: boolean;
  voice_enabled: boolean;
  stt_enabled: boolean;
  tts_enabled: boolean;
  stt_provider?: string | null;
  tts_provider?: string | null;
  detail?: string | null;
}

interface VoiceWsChunkPayload {
  type: "voice_chunk";
  audio_base64: string;
  mime_type: string;
  language: string;
  dispatch_to_agents: boolean;
  target_mode: "swarm" | "orchestrator";
  preferred_stt_provider?: "auto" | "grok" | "deepgram" | "openai";
  preferred_tts_provider?: "auto" | "grok" | "elevenlabs" | "openai";
  latency_mode?: "balanced" | "fast";
  tts_voice_id?: string;
  tts_language?: string;
  tts_tone?: string;
  session_id?: string;
}

interface BrowserSpeechRecognitionResultItem {
  readonly transcript?: string;
}

interface BrowserSpeechRecognitionResultListItem {
  readonly isFinal?: boolean;
  readonly 0?: BrowserSpeechRecognitionResultItem;
}

interface BrowserSpeechRecognitionEventLike {
  readonly resultIndex: number;
  readonly results: ArrayLike<BrowserSpeechRecognitionResultListItem>;
}

interface BrowserSpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: BrowserSpeechRecognitionEventLike) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}

type BrowserSpeechRecognitionCtor = new () => BrowserSpeechRecognitionLike;

function pickRecorderMimeType(): string {
  if (typeof MediaRecorder === "undefined") {
    return "";
  }
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
  for (const candidate of candidates) {
    if (MediaRecorder.isTypeSupported(candidate)) {
      return candidate;
    }
  }
  return "";
}

const MIN_VOICE_BLOB_BYTES = 1024;
/** Max JSON payload for one STT upload (~1.2 MB base64) — keeps nginx/Next under limits after WAV transcode. */
const MAX_VOICE_PAYLOAD_CHARS = 1_600_000;
/** Auto-stop one voice turn after this many seconds (Grok-like short utterances). */
const MAX_UTTERANCE_SECONDS = 12;

function sttLanguageFromVoicePref(voiceLang: string): string {
  const raw = voiceLang.trim().toLowerCase();
  if (!raw || raw === "auto") {
    return "auto";
  }
  return raw.split("-")[0] ?? "auto";
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const raw = typeof reader.result === "string" ? reader.result : "";
      const encoded = raw.includes(",") ? raw.split(",")[1] : raw;
      if (!encoded) {
        reject(new Error("Empty audio payload"));
        return;
      }
      resolve(encoded);
    };
    reader.onerror = () => reject(new Error("Audio read failed"));
    reader.readAsDataURL(blob);
  });
}

export const VoiceSessionControls = forwardRef<VoiceSessionControlsHandle, VoiceSessionControlsProps>(
  function VoiceSessionControls(
    {
      sessionId,
      dispatchToAgents = false,
      targetMode = "swarm",
      allowBrowserFallback = false,
      preferredSttProvider = "auto",
      preferredTtsProvider = "auto",
      latencyMode = "balanced",
      vadThreshold = 0.35,
      silenceDurationMs = 450,
      ttsVoiceId = "eve",
      ttsLanguage = "auto",
      ttsTone = "none",
      disabled = false,
      compact = false,
      className,
      remoteTranscript = null,
      remoteError = null,
      onTranscript,
      onRecordingChange,
      onRecordingSeconds,
      maxRecordingSeconds,
      onRecordingLimitReached,
      label = "Voice",
    },
    ref,
  ): JSX.Element {
    const [recording, setRecording] = useState(false);
    const [transcribing, setTranscribing] = useState(false);
    const [lastText, setLastText] = useState<string>("");
    const [error, setError] = useState<string | null>(null);
    const [levels, setLevels] = useState<number[]>([3, 7, 5, 8, 4, 6]);
    const [serverVoice, setServerVoice] = useState<VoiceCapabilitiesResponse | null>(null);
    const recorderRef = useRef<MediaRecorder | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const recognitionRef = useRef<BrowserSpeechRecognitionLike | null>(null);
    const pendingRef = useRef<Promise<void>>(Promise.resolve());
    const audioContextRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const rafRef = useRef<number | null>(null);
    const vadTimerRef = useRef<number | null>(null);
    const levelRef = useRef<number>(0);
    const speechActiveRef = useRef<boolean>(false);
    const lastSpeechAtRef = useRef<number>(0);
    const recordingStartedAtRef = useRef<number | null>(null);
    const activeMimeRef = useRef<string>("audio/webm");

    const speechRecognitionCtor: BrowserSpeechRecognitionCtor | null =
      typeof window !== "undefined"
        ? (((window as unknown as { SpeechRecognition?: BrowserSpeechRecognitionCtor }).SpeechRecognition ??
            (window as unknown as { webkitSpeechRecognition?: BrowserSpeechRecognitionCtor }).webkitSpeechRecognition) ??
          null)
        : null;

    useEffect(() => {
      let mounted = true;
      void hiveGet<VoiceCapabilitiesResponse>("ballroom/voice/capabilities")
        .then((caps) => {
          if (!mounted) return;
          setServerVoice(caps);
        })
        .catch(() => {
          if (!mounted) return;
          setServerVoice(null);
        });
      return () => {
        mounted = false;
      };
    }, []);

    useEffect(() => {
      if (remoteTranscript && remoteTranscript.trim()) {
        setLastText(remoteTranscript.trim());
        setTranscribing(false);
        setError(null);
      }
    }, [remoteTranscript]);

    useEffect(() => {
      if (remoteError && remoteError.trim()) {
        setError(remoteError.trim());
        setTranscribing(false);
      }
    }, [remoteError]);

    const canUseBackendVoice = !!serverVoice?.stt_enabled && typeof window !== "undefined" && !!window.MediaRecorder;
    const canUseVoice = canUseBackendVoice || (allowBrowserFallback && !!speechRecognitionCtor);
    const canRecord = canUseVoice && !disabled;

    const stopMeter = useCallback(() => {
      if (rafRef.current !== null) {
        window.cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      analyserRef.current = null;
      if (audioContextRef.current) {
        void audioContextRef.current.close();
        audioContextRef.current = null;
      }
      setLevels([3, 7, 5, 8, 4, 6]);
    }, []);

    const stopVadTimer = useCallback(() => {
      if (vadTimerRef.current !== null) {
        window.clearInterval(vadTimerRef.current);
        vadTimerRef.current = null;
      }
    }, []);

    const startMeter = useCallback((stream: MediaStream) => {
      if (typeof window === "undefined") {
        return;
      }
      const context = new window.AudioContext();
      audioContextRef.current = context;
      const source = context.createMediaStreamSource(stream);
      const analyser = context.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;
      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        const node = analyserRef.current;
        if (!node) {
          return;
        }
        node.getByteFrequencyData(data);
        const chunk = Math.max(1, Math.floor(data.length / 6));
        const next: number[] = [];
        for (let i = 0; i < 6; i += 1) {
          const from = i * chunk;
          const to = Math.min(data.length, from + chunk);
          let sum = 0;
          for (let j = from; j < to; j += 1) {
            sum += data[j] ?? 0;
          }
          const avg = sum / Math.max(1, to - from);
          next.push(Math.max(3, Math.round((avg / 255) * 18)));
        }
        levelRef.current = next.reduce((acc, val) => acc + val, 0) / Math.max(1, next.length) / 18;
        setLevels(next);
        rafRef.current = window.requestAnimationFrame(tick);
      };
      tick();
    }, []);

    const cleanupRecorder = useCallback(() => {
      stopVadTimer();
      recorderRef.current = null;
      recordingStartedAtRef.current = null;
      speechActiveRef.current = false;
      lastSpeechAtRef.current = 0;
      if (recognitionRef.current) {
        recognitionRef.current.onresult = null;
        recognitionRef.current.onerror = null;
        recognitionRef.current.onend = null;
        recognitionRef.current.stop();
        recognitionRef.current = null;
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
      stopMeter();
    }, [stopMeter, stopVadTimer]);

    useEffect(() => cleanupRecorder, [cleanupRecorder]);

    useEffect(() => {
      onRecordingChange?.(recording);
    }, [onRecordingChange, recording]);

    useEffect(() => {
      if (!recording) {
        onRecordingSeconds?.(0);
        return;
      }
      const tick = () => {
        const started = recordingStartedAtRef.current;
        if (!started) {
          return;
        }
        onRecordingSeconds?.(Math.max(0, Math.floor((Date.now() - started) / 1000)));
      };
      tick();
      const timer = window.setInterval(tick, 1000);
      return () => window.clearInterval(timer);
    }, [onRecordingSeconds, recording]);

    useEffect(() => {
      if (!recording || !maxRecordingSeconds || maxRecordingSeconds <= 0) {
        return;
      }
      const timer = window.setInterval(() => {
        const started = recordingStartedAtRef.current;
        if (!started) {
          return;
        }
        const elapsed = Math.floor((Date.now() - started) / 1000);
        if (elapsed >= MAX_UTTERANCE_SECONDS) {
          const recorder = recorderRef.current;
          if (recorder && recorder.state !== "inactive") {
            recorder.stop();
          }
          return;
        }
        if (elapsed < maxRecordingSeconds) {
          return;
        }
        const recorder = recorderRef.current;
        if (recorder && recorder.state !== "inactive") {
          recorder.stop();
        }
        onRecordingLimitReached?.();
      }, 500);
      return () => window.clearInterval(timer);
    }, [maxRecordingSeconds, onRecordingLimitReached, recording]);

    const enqueueTranscribe = useCallback(
      (blob: Blob) => {
        if (blob.size < MIN_VOICE_BLOB_BYTES) {
          return;
        }
        pendingRef.current = pendingRef.current.then(async () => {
          setTranscribing(true);
          setError(null);
          try {
            const audioBase64 = await blobToBase64(blob);
            if (audioBase64.length > MAX_VOICE_PAYLOAD_CHARS) {
              setError("Voice clip too long — speak in shorter turns (under 12 seconds).");
              return;
            }
            const payload: VoiceWsChunkPayload = {
              type: "voice_chunk",
              audio_base64: audioBase64,
              mime_type: blob.type || activeMimeRef.current || "audio/webm",
              language: sttLanguageFromVoicePref(ttsLanguage ?? "auto"),
              dispatch_to_agents: dispatchToAgents,
              target_mode: targetMode,
              preferred_stt_provider: preferredSttProvider,
              preferred_tts_provider: preferredTtsProvider,
              latency_mode: latencyMode,
              tts_voice_id: ttsVoiceId,
              tts_language: ttsLanguage,
              tts_tone: ttsTone,
            };
            if (sessionId) {
              payload.session_id = sessionId;
            }
            // Always use REST — cookie auth via /api/proxy is reliable; WS STT duplicates work.
            const out = await hivePostJson<VoiceTranscribeResponse>("ballroom/voice/transcribe", payload);
            if (out.skipped) {
              return;
            }
            const text = (out.text ?? "").trim();
            if (text) {
              setLastText(text);
              onTranscript?.(text);
            }
          } catch (exc) {
            const detail =
              exc instanceof HiveApiError ? exc.message : exc instanceof Error ? exc.message : "Voice upload failed.";
            setError(detail);
          } finally {
            setTranscribing(false);
          }
        });
      },
      [
        dispatchToAgents,
        latencyMode,
        onTranscript,
        preferredSttProvider,
        preferredTtsProvider,
        sessionId,
        targetMode,
        ttsLanguage,
        ttsTone,
        ttsVoiceId,
      ],
    );

    const stopRecording = useCallback(() => {
      const recorder = recorderRef.current;
      if (recorder && recorder.state !== "inactive") {
        recorder.stop();
        return;
      }
      recordingStartedAtRef.current = null;
      cleanupRecorder();
      setRecording(false);
    }, [cleanupRecorder]);

    const startVadTimer = useCallback(() => {
      stopVadTimer();
      const threshold = Math.max(0.05, Math.min(1.0, vadThreshold));
      const silenceLimit = Math.max(300, Math.min(4000, silenceDurationMs));
      vadTimerRef.current = window.setInterval(() => {
        const recorder = recorderRef.current;
        if (!recorder || recorder.state !== "recording") {
          return;
        }
        const now = Date.now();
        const level = levelRef.current;
        if (level >= threshold) {
          speechActiveRef.current = true;
          lastSpeechAtRef.current = now;
          return;
        }
        if (!speechActiveRef.current) {
          return;
        }
        if (lastSpeechAtRef.current > 0 && now - lastSpeechAtRef.current >= silenceLimit) {
          speechActiveRef.current = false;
          lastSpeechAtRef.current = 0;
          stopRecording();
        }
      }, 120);
    }, [silenceDurationMs, stopVadTimer, stopRecording, vadThreshold]);

    const startRecording = useCallback(async () => {
      if (!canRecord || recording) {
        return;
      }
      setError(null);
      if (!canUseBackendVoice && allowBrowserFallback && speechRecognitionCtor) {
        try {
          const recognition = new speechRecognitionCtor();
          recognitionRef.current = recognition;
          recognition.lang = "sk-SK";
          recognition.continuous = true;
          recognition.interimResults = true;
          setRecording(true);
          recognition.onresult = (event: BrowserSpeechRecognitionEventLike) => {
            const idx = event.resultIndex;
            const next = event.results[idx];
            if (!next) return;
            const text = String(next[0]?.transcript || "").trim();
            if (!text) return;
            setLastText(text);
            onTranscript?.(text);
            if (dispatchToAgents && sessionId && next.isFinal) {
              void hivePostJson("ballroom/message", {
                session_id: sessionId,
                text,
                mode: targetMode,
                preferred_tts_provider: preferredTtsProvider,
                latency_mode: latencyMode,
                tts_voice_id: ttsVoiceId,
                tts_language: ttsLanguage,
                tts_tone: ttsTone,
              }).catch(() => {});
            }
          };
          recognition.onerror = () => setError("Browser speech recognition failed.");
          recognition.onend = () => {
            setRecording(false);
            cleanupRecorder();
          };
          recognition.start();
          recordingStartedAtRef.current = Date.now();
          return;
        } catch (exc) {
          setError(exc instanceof Error ? exc.message : "Speech recognition unavailable.");
          setRecording(false);
          cleanupRecorder();
          return;
        }
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        streamRef.current = stream;
        startMeter(stream);
        const recorderMime = pickRecorderMimeType();
        const recorder = recorderMime
          ? new MediaRecorder(stream, { mimeType: recorderMime })
          : new MediaRecorder(stream);
        activeMimeRef.current = recorder.mimeType || recorderMime || "audio/webm";
        recorderRef.current = recorder;
        recorder.ondataavailable = (event: BlobEvent) => {
          if (!event.data || event.data.size < MIN_VOICE_BLOB_BYTES) {
            return;
          }
          enqueueTranscribe(event.data);
        };
        recorder.onstop = () => {
          setRecording(false);
          cleanupRecorder();
        };
        recorder.start();
        startVadTimer();
        recordingStartedAtRef.current = Date.now();
        setRecording(true);
      } catch (exc) {
        const detail = exc instanceof Error ? exc.message : "Microphone access denied.";
        setError(detail);
        cleanupRecorder();
        setRecording(false);
      }
    }, [
      allowBrowserFallback,
      canRecord,
      canUseBackendVoice,
      cleanupRecorder,
      dispatchToAgents,
      enqueueTranscribe,
      latencyMode,
      onTranscript,
      recording,
      preferredTtsProvider,
      sessionId,
      speechRecognitionCtor,
      startMeter,
      startVadTimer,
      targetMode,
      ttsLanguage,
      ttsTone,
      ttsVoiceId,
    ]);

    useImperativeHandle(
      ref,
      () => ({
        toggleRecording: () => {
          if (recording) {
            stopRecording();
          } else {
            void startRecording();
          }
        },
        isRecording: () => recording,
      }),
      [recording, startRecording, stopRecording],
    );

    const statusLabel = useMemo(() => {
      if (!canUseVoice) {
        const serverDetail = (serverVoice?.detail ?? "").trim();
        if (serverDetail) {
          return serverDetail;
        }
        if (!canUseBackendVoice && typeof window !== "undefined" && !window.MediaRecorder) {
          return "Voice capture unavailable in this browser (MediaRecorder unsupported).";
        }
        if (!canUseBackendVoice && !allowBrowserFallback) {
          return "Server voice unavailable. Enable VOICE_ENABLED and STT/TTS keys on backend.";
        }
        return "Voice capture unavailable in this browser.";
      }
      if (!canUseBackendVoice && allowBrowserFallback && speechRecognitionCtor) {
        const reason = (serverVoice?.detail ?? "").trim();
        if (reason) {
          return `Browser speech mode active (${reason})`;
        }
        return "Browser speech mode active (server STT unavailable).";
      }
      if (!canUseBackendVoice && !allowBrowserFallback) {
        return (serverVoice?.detail ?? "Server speech mode unavailable right now.").trim();
      }
      if (recording && transcribing) {
        return "Listening + transcribing…";
      }
      if (recording) {
        return "Listening… stop speaking to auto-send";
      }
      if (transcribing) {
        return "Transcribing…";
      }
      return "Ready for voice input.";
    }, [allowBrowserFallback, canUseBackendVoice, canUseVoice, recording, serverVoice?.detail, speechRecognitionCtor, transcribing]);

    return (
      <div className={cn("rounded-xl border border-(--qs-border) bg-(--qs-surface-2)/55 p-3", className)}>
        <div className={cn("flex flex-wrap items-center justify-between gap-2", compact && "gap-1.5")}>
          <div>
            <p className="text-[11px] uppercase tracking-widest text-(--qs-text-3)">{label}</p>
            <p className="text-[11px] text-(--qs-text-3)">{statusLabel}</p>
          </div>
          <button
            type="button"
            className={cn(
              "qs-btn qs-btn--sm",
              recording ? "qs-btn--danger" : "qs-btn--ghost",
              !canRecord && "opacity-45",
            )}
            disabled={!canRecord}
            onClick={() => (recording ? stopRecording() : void startRecording())}
          >
            {recording ? "Stop voice" : "Voice input"}
          </button>
        </div>

        <div className="mt-2 flex items-end gap-1 rounded-lg border border-(--qs-border) bg-(--qs-surface-2)/40 px-2 py-2">
          {levels.map((level, idx) => (
            <span
              key={idx}
              className={cn("w-1.5 rounded-sm transition-all", recording ? "bg-pollen" : "bg-(--qs-border)")}
              style={{ height: `${Math.max(3, level)}px` }}
            />
          ))}
        </div>

        <p className="mt-2 min-h-6 text-xs text-(--qs-text)">
          {lastText ? `“${lastText}”` : "Live transcript will appear here."}
        </p>
        {error ? <p className="mt-1 text-[11px] text-(--qs-red)">{error}</p> : null}
      </div>
    );
  },
);

VoiceSessionControls.displayName = "VoiceSessionControls";
