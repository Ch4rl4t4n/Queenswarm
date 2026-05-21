"use client";

import { Loader2Icon, Pause, Play, Volume2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { usePlatform } from "@/components/hive/platform-context";
import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";

interface OvernightVoiceReportPayload {
  available: boolean;
  batch_id?: string | null;
  script_text?: string;
  audio_base64?: string;
  content_type?: string;
  provider?: string;
  voice_disabled?: boolean;
}

interface OvernightVoiceReportPlayerProps {
  /** When false, hide the control entirely (parent already knows report exists). */
  enabled?: boolean;
  className?: string;
}

/** Play Ballroom TTS briefing for the latest overnight swarm report. */
export function OvernightVoiceReportPlayer({
  enabled = true,
  className,
}: OvernightVoiceReportPlayerProps): JSX.Element | null {
  const { hasFeature } = usePlatform();
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [loading, setLoading] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [payload, setPayload] = useState<OvernightVoiceReportPayload | null>(null);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const loadAndPlay = useCallback(async () => {
    if (playing && audioRef.current) {
      audioRef.current.pause();
      setPlaying(false);
      return;
    }
    setLoading(true);
    setErr(null);
    try {
      const body = await hiveGet<OvernightVoiceReportPayload>("dump-sleep/overnight-report/voice");
      setPayload(body);
      if (!body.available) {
        setErr("No overnight report available for voice briefing.");
        return;
      }
      if (body.voice_disabled || !body.audio_base64) {
        setErr("Voice pipeline disabled — read the text briefing instead.");
        return;
      }
      const mime = body.content_type || "audio/mpeg";
      const src = `data:${mime};base64,${body.audio_base64}`;
      if (audioRef.current) {
        audioRef.current.pause();
      }
      const audio = new Audio(src);
      audioRef.current = audio;
      audio.onended = () => setPlaying(false);
      audio.onpause = () => setPlaying(false);
      audio.onplay = () => setPlaying(true);
      await audio.play();
      setPlaying(true);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Voice briefing unavailable.");
      setPlaying(false);
    } finally {
      setLoading(false);
    }
  }, [playing]);

  if (!enabled || !hasFeature("overnight_voice_report")) {
    return null;
  }

  return (
    <div className={className}>
      <button
        type="button"
        className="qs-btn qs-btn--secondary qs-btn--sm inline-flex items-center gap-2"
        disabled={loading}
        onClick={() => void loadAndPlay()}
      >
        {loading ? (
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden />
        ) : playing ? (
          <Pause className="h-4 w-4" aria-hidden />
        ) : (
          <Play className="h-4 w-4" aria-hidden />
        )}
        {playing ? "Pause briefing" : "Listen to briefing"}
        <Volume2 className="h-3.5 w-3.5 text-cyan" aria-hidden />
      </button>
      {payload?.provider ? (
        <V4Badge tone="info" className="ml-2 align-middle">
          {payload.provider}
        </V4Badge>
      ) : null}
      {err ? <p className="mt-2 text-[11px] text-(--qs-red)">{err}</p> : null}
    </div>
  );
}
