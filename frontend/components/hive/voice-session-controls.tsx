"use client";

import type { JSX } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { HiveApiError, hivePostJson } from "@/lib/api";
import { VOICE_ENABLED } from "@/lib/feature-flags";
import { cn } from "@/lib/utils";

interface VoiceSessionControlsProps {
  readonly sessionId?: string | null;
  readonly dispatchToAgents?: boolean;
  readonly disabled?: boolean;
  readonly compact?: boolean;
  readonly className?: string;
  readonly onTranscript?: (text: string) => void;
  readonly label?: string;
}

interface VoiceTranscribeResponse {
  text?: string;
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

export function VoiceSessionControls({
  sessionId,
  dispatchToAgents = false,
  disabled = false,
  compact = false,
  className,
  onTranscript,
  label = "Voice",
}: VoiceSessionControlsProps): JSX.Element {
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [lastText, setLastText] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [levels, setLevels] = useState<number[]>([3, 7, 5, 8, 4, 6]);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const pendingRef = useRef<Promise<void>>(Promise.resolve());
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const rafRef = useRef<number | null>(null);

  const canUseVoice = VOICE_ENABLED && typeof window !== "undefined" && !!window.MediaRecorder;
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
      setLevels(next);
      rafRef.current = window.requestAnimationFrame(tick);
    };
    tick();
  }, []);

  const cleanupRecorder = useCallback(() => {
    recorderRef.current = null;
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    stopMeter();
  }, [stopMeter]);

  useEffect(() => cleanupRecorder, [cleanupRecorder]);

  const enqueueTranscribe = useCallback(
    (blob: Blob) => {
      pendingRef.current = pendingRef.current.then(async () => {
        setTranscribing(true);
        setError(null);
        try {
          const audioBase64 = await blobToBase64(blob);
          const payload: Record<string, unknown> = {
            audio_base64: audioBase64,
            mime_type: blob.type || "audio/webm",
            language: "sk",
            dispatch_to_agents: dispatchToAgents,
          };
          if (sessionId) {
            payload.session_id = sessionId;
          }
          const out = await hivePostJson<VoiceTranscribeResponse>("ballroom/voice/transcribe", payload);
          const text = (out.text ?? "").trim();
          if (text) {
            setLastText(text);
            onTranscript?.(text);
          }
        } catch (exc) {
          const detail = exc instanceof HiveApiError ? exc.message : exc instanceof Error ? exc.message : "Voice upload failed.";
          setError(detail);
        } finally {
          setTranscribing(false);
        }
      });
    },
    [dispatchToAgents, onTranscript, sessionId],
  );

  const startRecording = useCallback(async () => {
    if (!canRecord || recording) {
      return;
    }
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      startMeter(stream);
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      recorderRef.current = recorder;
      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data && event.data.size > 0) {
          enqueueTranscribe(event.data);
        }
      };
      recorder.onstop = () => {
        setRecording(false);
        cleanupRecorder();
      };
      recorder.start(1500);
      setRecording(true);
    } catch (exc) {
      const detail = exc instanceof Error ? exc.message : "Microphone access denied.";
      setError(detail);
      cleanupRecorder();
      setRecording(false);
    }
  }, [canRecord, cleanupRecorder, enqueueTranscribe, recording, startMeter]);

  const stopRecording = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    } else {
      cleanupRecorder();
      setRecording(false);
    }
  }, [cleanupRecorder]);

  const statusLabel = useMemo(() => {
    if (!VOICE_ENABLED) {
      return "Voice disabled by feature flag.";
    }
    if (!canUseVoice) {
      return "Voice capture unavailable in this browser.";
    }
    if (recording && transcribing) {
      return "Listening + transcribing…";
    }
    if (recording) {
      return "Listening…";
    }
    if (transcribing) {
      return "Transcribing last chunk…";
    }
    return "Ready for voice input.";
  }, [canUseVoice, recording, transcribing]);

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

      <div className="mt-2 flex items-end gap-1 rounded-lg border border-(--qs-border)/70 bg-black/25 px-2 py-2">
        {levels.map((level, idx) => (
          <span
            key={idx}
            className={cn("w-1.5 rounded-sm transition-all", recording ? "bg-[#00FFFF]" : "bg-(--qs-border)")}
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
}
