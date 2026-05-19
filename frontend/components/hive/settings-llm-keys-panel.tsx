"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { QsSelect } from "@/components/ui/qs-select";
import { InfoHint } from "@/components/hive/info-hint";
import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveDelete, hiveGet, hivePatchJson, hivePostJson, hivePutJson } from "@/lib/api";
import type { LlmKeyMaskRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

type ProviderId = "grok" | "anthropic" | "openai" | "deepgram" | "elevenlabs";
type SttProviderPreference = "auto" | "grok" | "deepgram" | "openai";
type TtsProviderPreference = "auto" | "grok" | "elevenlabs" | "openai";

interface VoiceProviderPreferences {
  stt_provider: SttProviderPreference;
  tts_provider: TtsProviderPreference;
  latency_mode: "balanced" | "fast";
  vad_threshold: number;
  silence_duration_ms: number;
  tts_voice_id: string;
  tts_language: string;
  tts_tone: string;
}

const PROVIDERS: ProviderId[] = ["grok", "anthropic", "openai", "deepgram", "elevenlabs"];

const STT_PROVIDER_OPTIONS: readonly { value: SttProviderPreference; label: string }[] = [
  { value: "auto", label: "Auto (Grok -> Deepgram -> OpenAI)" },
  { value: "grok", label: "Grok STT" },
  { value: "deepgram", label: "Deepgram" },
  { value: "openai", label: "OpenAI Whisper" },
];

const TTS_PROVIDER_OPTIONS: readonly { value: TtsProviderPreference; label: string }[] = [
  { value: "auto", label: "Auto (Grok -> ElevenLabs -> OpenAI)" },
  { value: "grok", label: "Grok TTS" },
  { value: "elevenlabs", label: "ElevenLabs" },
  { value: "openai", label: "OpenAI TTS" },
];

const LATENCY_MODE_OPTIONS = [
  { value: "balanced", label: "Balanced (higher quality)" },
  { value: "fast", label: "Fast (lower latency)" },
] as const;

const VOICE_PROFILE_OPTIONS = [
  { value: "auto", label: "Auto (based on tone)" },
  { value: "eve", label: "Eve" },
  { value: "ara", label: "Ara" },
  { value: "leo", label: "Leo" },
  { value: "rex", label: "Rex" },
  { value: "sal", label: "Sal" },
] as const;

const VOICE_TONE_OPTIONS = [
  { value: "none", label: "Neutral" },
  { value: "warm", label: "Warm" },
  { value: "friendly", label: "Friendly" },
  { value: "professional", label: "Professional" },
  { value: "authoritative", label: "Authoritative" },
  { value: "expressive", label: "Expressive" },
  { value: "casual", label: "Casual" },
] as const;

const VOICE_LANGUAGE_OPTIONS = [
  { value: "auto", label: "Auto" },
  { value: "sk", label: "Slovak (sk)" },
  { value: "en", label: "English (en)" },
] as const;
const PROVIDER_COPY: Record<
  ProviderId,
  { title: { en: string; sk: string }; hint: { en: string; sk: string } }
> = {
  grok: {
    title: { en: "Grok (xAI)", sk: "Grok (xAI)" },
    hint: { en: "Primary routing - persisted in hive vault.", sk: "Primarny routing - ulozene v hive vault." },
  },
  anthropic: {
    title: { en: "Claude - Anthropic", sk: "Claude - Anthropic" },
    hint: { en: "Admin-only upsert unless env already supplies credential.", sk: "Zapis len pre admina, ak credential uz nie je v env." },
  },
  openai: {
    title: { en: "OpenAI - GPT-4o mini", sk: "OpenAI - GPT-4o mini" },
    hint: { en: "Cheap simulations / parity checks.", sk: "Lacne simulacie a parity kontroly." },
  },
  deepgram: {
    title: { en: "Deepgram - STT", sk: "Deepgram - STT" },
    hint: { en: "Server-side speech-to-text for Ballroom voice input.", sk: "Serverovy speech-to-text pre hlasovy vstup v Ballroom." },
  },
  elevenlabs: {
    title: { en: "ElevenLabs - TTS", sk: "ElevenLabs - TTS" },
    hint: { en: "High-fidelity server-side speech output.", sk: "Kvalitny serverovy speech vystup." },
  },
};

const PROVIDER_SKINS: Record<
  ProviderId,
  { logo: string; bgColor: string; borderColor: string; textColor: string }
> = {
  grok: {
    logo: "xAI",
    bgColor: "#0a0a12",
    borderColor: "rgb(0 229 255 / 0.35)",
    textColor: "#e8e8f0",
  },
  anthropic: {
    logo: "Cl",
    bgColor: "#1a1420",
    borderColor: "rgb(255 184 0 / 0.28)",
    textColor: "#FFB800",
  },
  openai: {
    logo: "GPT",
    bgColor: "#0f1a14",
    borderColor: "rgb(0 255 136 / 0.28)",
    textColor: "#00FF88",
  },
  deepgram: {
    logo: "DG",
    bgColor: "#0f1326",
    borderColor: "rgb(83 124 255 / 0.35)",
    textColor: "#7da2ff",
  },
  elevenlabs: {
    logo: "11",
    bgColor: "#20160f",
    borderColor: "rgb(255 169 94 / 0.35)",
    textColor: "#ffb56e",
  },
};

export function SettingsLlmKeysPanel() {
  const { language } = useUiLanguage();
  const latencyModeOptions = useMemo(
    () =>
      language === "sk"
        ? [
            { value: "balanced", label: "Balanced (vyssia kvalita)" },
            { value: "fast", label: "Fast (nizsia latencia)" },
          ]
        : [...LATENCY_MODE_OPTIONS],
    [language],
  );
  const voiceProfileOptions = useMemo(
    () =>
      VOICE_PROFILE_OPTIONS.map((row) =>
        row.value === "auto"
          ? { ...row, label: language === "sk" ? "Auto (podla tone)" : "Auto (based on tone)" }
          : row,
      ),
    [language],
  );
  const voiceToneOptions = useMemo(
    () =>
      language === "sk"
        ? [
            { value: "none", label: "Neutralny" },
            { value: "warm", label: "Teply" },
            { value: "friendly", label: "Priatelsky" },
            { value: "professional", label: "Profesionalny" },
            { value: "authoritative", label: "Autoritativny" },
            { value: "expressive", label: "Expresivny" },
            { value: "casual", label: "Neformalny" },
          ]
        : [...VOICE_TONE_OPTIONS],
    [language],
  );
  const [keys, setKeys] = useState<LlmKeyMaskRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [voicePrefsBusy, setVoicePrefsBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [voicePrefs, setVoicePrefs] = useState<VoiceProviderPreferences>({
    stt_provider: "auto",
    tts_provider: "auto",
    latency_mode: "balanced",
    vad_threshold: 0.7,
    silence_duration_ms: 700,
    tts_voice_id: "eve",
    tts_language: "auto",
    tts_tone: "none",
  });

  const [inputs, setInputs] = useState<Record<string, string>>({
    grok: "",
    anthropic: "",
    openai: "",
    deepgram: "",
    elevenlabs: "",
  });
  const [labels, setLabels] = useState<Record<string, string>>({
    grok: "",
    anthropic: "",
    openai: "",
    deepgram: "",
    elevenlabs: "",
  });
  const [primaryFlags, setPrimaryFlags] = useState<Record<string, boolean>>({
    grok: true,
    anthropic: false,
    openai: false,
    deepgram: false,
    elevenlabs: false,
  });
  const [testMsg, setTestMsg] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    try {
      const [rows, prefs] = await Promise.all([
        hiveGet<{ keys: LlmKeyMaskRow[] }>("llm-keys"),
        hiveGet<VoiceProviderPreferences>("llm-keys/voice-preferences"),
      ]);
      setKeys(rows.keys ?? []);
      const nextLabels: Record<string, string> = {
        grok: "",
        anthropic: "",
        openai: "",
        deepgram: "",
        elevenlabs: "",
      };
      const nextPrimary: Record<string, boolean> = {
        grok: true,
        anthropic: false,
        openai: false,
        deepgram: false,
        elevenlabs: false,
      };
      for (const row of rows.keys ?? []) {
        if (!row.provider) {
          continue;
        }
        nextLabels[row.provider] = typeof row.label === "string" ? row.label : "";
        nextPrimary[row.provider] = Boolean(row.is_primary);
      }
      setLabels(nextLabels);
      setPrimaryFlags(nextPrimary);
      setVoicePrefs({
        stt_provider: prefs.stt_provider ?? "auto",
        tts_provider: prefs.tts_provider ?? "auto",
        latency_mode: prefs.latency_mode ?? "balanced",
        vad_threshold: typeof prefs.vad_threshold === "number" ? prefs.vad_threshold : 0.7,
        silence_duration_ms: typeof prefs.silence_duration_ms === "number" ? prefs.silence_duration_ms : 700,
        tts_voice_id: typeof prefs.tts_voice_id === "string" ? prefs.tts_voice_id : "eve",
        tts_language: typeof prefs.tts_language === "string" ? prefs.tts_language : "auto",
        tts_tone: typeof prefs.tts_tone === "string" ? prefs.tts_tone : "none",
      });
      setErr(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Load failed";
      setErr(msg);
      setKeys([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function rowFor(provider: string): LlmKeyMaskRow | undefined {
    return keys.find((k) => k.provider === provider);
  }

  async function saveProviderMeta(provider: ProviderId): Promise<void> {
    setBusy(true);
    try {
      await hivePatchJson(`llm-keys/${provider}/meta`, {
        label: labels[provider]?.trim() ?? "",
        is_primary: Boolean(primaryFlags[provider]),
      });
      toast.success(language === "sk" ? "Metadata uložená." : "Provider metadata saved.");
      await load();
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Save failed";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function save(provider: ProviderId): Promise<void> {
    const trimmed = inputs[provider]?.trim() ?? "";
    if (trimmed.length < 12) {
      toast.error("Paste a complete API secret (minimum 12 characters).");
      return;
    }
    setBusy(true);
    try {
      await hivePostJson("llm-keys/", {
        provider,
        label: labels[provider]?.trim() ?? "",
        api_key: trimmed,
        is_primary: provider === "grok" ? primaryFlags[provider] !== false : Boolean(primaryFlags[provider]),
      });
      setInputs((s) => ({ ...s, [provider]: "" }));
      setTestMsg((m) => ({ ...m, [provider]: "" }));
      toast.success(`${provider.toUpperCase()} credential stored.`);
      await load();
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Save failed";
      if (e instanceof HiveApiError && e.status === 403) {
        toast.error("Admin privileges required for this provider.");
      } else {
        toast.error(msg);
      }
    } finally {
      setBusy(false);
    }
  }

  async function clearProvider(provider: ProviderId): Promise<void> {
    if (!window.confirm(`Remove vault override for ${provider}?`)) {
      return;
    }
    setBusy(true);
    try {
      await hiveDelete(`llm-keys/${provider}`);
      setTestMsg((m) => ({ ...m, [provider]: "" }));
      toast.success("Credential cleared.");
      await load();
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Delete failed";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function testProvider(provider: ProviderId): Promise<void> {
    setBusy(true);
    try {
      const res = await hivePostJson<{ status?: string; error?: string; response?: string }>(`llm-keys/test/${provider}`, {});
      const ok = res.status === "ok";
      const line = ok ? `✅ CONNECTED (${res.response ?? "ping ok"})` : `❌ ${res.error ?? "ping failed"}`;
      setTestMsg((m) => ({ ...m, [provider]: line }));
      toast.message(ok ? "LLM reachable" : "LLM test failed");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Test failed";
      setTestMsg((m) => ({ ...m, [provider]: `❌ ${msg}` }));
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function saveVoicePreferences(): Promise<void> {
    setVoicePrefsBusy(true);
    try {
      await hivePutJson<VoiceProviderPreferences>("llm-keys/voice-preferences", voicePrefs);
      toast.success(language === "sk" ? "Voice preferencie uložené." : "Voice preferences saved.");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Save failed";
      toast.error(msg);
    } finally {
      setVoicePrefsBusy(false);
    }
  }

  if (err && keys.length === 0) {
    return (
      <V4Card className="border-danger/30 bg-danger/6 text-danger">
        LLM keys: {err}
      </V4Card>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <p className="text-sm text-(--qs-text-3)">
        Credentials call{" "}
        <span className="font-mono text-xs text-pollen">POST /api/v1/llm-keys</span> through the hive proxy · masked
        values never round-trip plaintext. Voice providers (Deepgram/ElevenLabs) are configurable here too.
      </p>

      <V4Card>
        <V4CardHeader
          as="h3"
          title={language === "sk" ? "Preferovaný voice provider (STT/TTS)" : "Preferred voice provider (STT/TTS)"}
          actions={
            <InfoHint
              title={{
                en: "How provider preference works",
                sk: "Ako funguje preferencia providerov",
              }}
              description={{
                en: "Choose which engine is tried first. If the preferred provider is unavailable or returns an error, server-side fallback is used automatically.",
                sk: "Vyberieš engine, ktorý sa má skúsiť ako prvý. Ak preferovaný provider nie je dostupný alebo zlyhá, server automaticky použije fallback.",
              }}
              options={{
                en: [
                  "Auto = Grok->Deepgram->OpenAI for STT and Grok->ElevenLabs->OpenAI for TTS",
                  "Use explicit provider to force first choice",
                ],
                sk: [
                  "Auto = Grok->Deepgram->OpenAI pre STT a Grok->ElevenLabs->OpenAI pre TTS",
                  "Explicitny provider vynuti prvu volbu",
                ],
              }}
            />
          }
        />
        <div className="v4-settings-llm-grid grid gap-3 md:grid-cols-2">
          <label className="block">
            <span className="qs-label">{language === "sk" ? "STT priorita" : "STT priority"}</span>
            <QsSelect
              value={voicePrefs.stt_provider}
              disabled={voicePrefsBusy}
              onValueChange={(next) =>
                setVoicePrefs((prev) => ({
                  ...prev,
                  stt_provider: next as SttProviderPreference,
                }))
              }
              options={STT_PROVIDER_OPTIONS}
            />
          </label>
          <label className="block">
            <span className="qs-label">{language === "sk" ? "TTS priorita" : "TTS priority"}</span>
            <QsSelect
              value={voicePrefs.tts_provider}
              disabled={voicePrefsBusy}
              onValueChange={(next) =>
                setVoicePrefs((prev) => ({
                  ...prev,
                  tts_provider: next as TtsProviderPreference,
                }))
              }
              options={TTS_PROVIDER_OPTIONS}
            />
          </label>
        </div>
        <label className="mt-3 block md:max-w-[280px]">
          <span className="qs-label">{language === "sk" ? "Rezim odozvy" : "Response mode"}</span>
          <QsSelect
            value={voicePrefs.latency_mode}
            disabled={voicePrefsBusy}
            onValueChange={(next) =>
              setVoicePrefs((prev) => ({
                ...prev,
                latency_mode: next as "balanced" | "fast",
              }))
            }
            options={latencyModeOptions}
          />
        </label>
        <div className="v4-settings-llm-grid mt-4 grid gap-3 md:grid-cols-2">
          <label className="block">
            <span className="qs-label">{language === "sk" ? "VAD threshold" : "VAD threshold"}</span>
            <input
              type="range"
              min={0.25}
              max={0.95}
              step={0.05}
              value={voicePrefs.vad_threshold}
              disabled={voicePrefsBusy}
              onChange={(event) =>
                setVoicePrefs((prev) => ({
                  ...prev,
                  vad_threshold: Number(event.target.value),
                }))
              }
              className="w-full"
            />
            <p className="mt-1 text-[11px] text-(--qs-text-3)">
              {language === "sk" ? "Citlivost hlasu" : "Voice sensitivity"}: {voicePrefs.vad_threshold.toFixed(2)}
            </p>
          </label>
          <label className="block">
            <span className="qs-label">{language === "sk" ? "Silence duration (ms)" : "Silence duration (ms)"}</span>
            <input
              type="number"
              min={300}
              max={4000}
              step={50}
              value={voicePrefs.silence_duration_ms}
              disabled={voicePrefsBusy}
              onChange={(event) =>
                setVoicePrefs((prev) => ({
                  ...prev,
                  silence_duration_ms: Math.max(100, Math.min(4000, Number(event.target.value) || 700)),
                }))
              }
              className="qs-input"
            />
          </label>
          <label className="block">
            <span className="qs-label">{language === "sk" ? "Voice profile" : "Voice profile"}</span>
            <QsSelect
              value={voicePrefs.tts_voice_id}
              disabled={voicePrefsBusy}
              onValueChange={(next) =>
                setVoicePrefs((prev) => ({
                  ...prev,
                  tts_voice_id: next,
                }))
              }
              options={voiceProfileOptions}
            />
          </label>
          <label className="block">
            <span className="qs-label">{language === "sk" ? "Voice tone" : "Voice tone"}</span>
            <QsSelect
              value={voicePrefs.tts_tone}
              disabled={voicePrefsBusy}
              onValueChange={(next) =>
                setVoicePrefs((prev) => ({
                  ...prev,
                  tts_tone: next,
                }))
              }
              options={voiceToneOptions}
            />
          </label>
          <label className="block md:max-w-[280px]">
            <span className="qs-label">{language === "sk" ? "Voice language" : "Voice language"}</span>
            <QsSelect
              value={voicePrefs.tts_language}
              disabled={voicePrefsBusy}
              onValueChange={(next) =>
                setVoicePrefs((prev) => ({
                  ...prev,
                  tts_language: next,
                }))
              }
              options={VOICE_LANGUAGE_OPTIONS}
            />
          </label>
        </div>
        <button
          type="button"
          disabled={voicePrefsBusy}
          onClick={() => void saveVoicePreferences()}
          className="qs-btn qs-btn--primary qs-btn--sm mt-3"
        >
          {language === "sk" ? "Uložiť voice preferencie" : "Save voice preferences"}
        </button>
      </V4Card>

      <div className="flex flex-col gap-4">
        {PROVIDERS.map((provider) => {
          const masked = rowFor(provider);
          const skin = PROVIDER_SKINS[provider];
          const copy = PROVIDER_COPY[provider];
          return (
            <V4Card key={provider}>
              <V4CardHeader
                as="h3"
                title={language === "sk" ? copy.title.sk : copy.title.en}
                description={language === "sk" ? copy.hint.sk : copy.hint.en}
                actions={
                  <div className="flex flex-wrap gap-2">
                    <button type="button" disabled={busy} onClick={() => void testProvider(provider)} className="qs-btn qs-btn--ghost qs-btn--sm">
                      Test
                    </button>
                    <button type="button" disabled={busy || !masked} onClick={() => void clearProvider(provider)} className="qs-btn qs-btn--ghost qs-btn--sm text-danger">
                      Remove
                    </button>
                  </div>
                }
              />
              <div className="mb-3 flex items-center gap-3">
                <div
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-[11px] font-bold"
                  style={{
                    background: skin.bgColor,
                    border: `1px solid ${skin.borderColor}`,
                    color: skin.textColor,
                  }}
                >
                  {skin.logo}
                </div>
                {masked?.api_key_masked ? <V4Badge tone="gold">vault</V4Badge> : <V4Badge tone="info">empty</V4Badge>}
              </div>

              <div className="mb-3">
                <label className="qs-label" htmlFor={`llm-label-${provider}`}>
                  Friendly label
                </label>
                <input
                  id={`llm-label-${provider}`}
                  type="text"
                  value={labels[provider] ?? ""}
                  disabled={busy}
                  placeholder={provider === "grok" ? "Primary" : ""}
                  onChange={(e) => setLabels((prev) => ({ ...prev, [provider]: e.target.value }))}
                  className="qs-input"
                />
                <label className="mt-2 flex items-center gap-2 text-[12px] text-(--qs-text-3)">
                  <input
                    type="checkbox"
                    checked={Boolean(primaryFlags[provider])}
                    disabled={busy}
                    onChange={(e) =>
                      setPrimaryFlags((prev) => ({
                        ...prev,
                        [provider]: e.target.checked,
                      }))
                    }
                  />
                  {language === "sk" ? "Primárny shard pre tento provider" : "Primary shard for this provider"}
                </label>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void saveProviderMeta(provider)}
                  className="qs-btn qs-btn--ghost qs-btn--sm mt-2"
                >
                  {language === "sk" ? "Uložiť label" : "Save label"}
                </button>
              </div>

              {masked?.api_key_masked ? (
                <p className="mb-3 font-mono text-[12px] text-(--qs-amber)">Saved secret {masked.api_key_masked}</p>
              ) : (
                <p className="mb-3 font-mono text-[11px] text-(--qs-text-3)">No credential stored for this shard.</p>
              )}

              <label className="qs-label" htmlFor={`llm-secret-${provider}`}>
                Paste new API secret
              </label>
              <input
                id={`llm-secret-${provider}`}
                type="password"
                disabled={busy}
                autoComplete="off"
                value={inputs[provider] ?? ""}
                onChange={(e) =>
                  setInputs((prev) => ({
                    ...prev,
                    [provider]: e.target.value,
                  }))
                }
                placeholder="Paste new API secret"
                className="qs-input"
              />

              <button type="button" disabled={busy} onClick={() => void save(provider)} className="qs-btn qs-btn--primary qs-btn--sm mt-3">
                Save key
              </button>

              {testMsg[provider] ? (
                <p
                  className={cn(
                    "mt-2 font-mono text-[11px]",
                    testMsg[provider].startsWith("✅") ? "text-(--qs-green)" : "text-(--qs-red)",
                  )}
                >
                  {testMsg[provider]}
                </p>
              ) : null}
            </V4Card>
          );
        })}
      </div>
    </div>
  );
}
