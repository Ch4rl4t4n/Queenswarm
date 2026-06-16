"use client";

import { ChevronDown } from "lucide-react";
import { useCallback, useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { toast } from "sonner";

import { CostGuardianRoutingPanel } from "@/components/hive/cost-guardian-routing-panel";
import { DatasetRecipeWizardPanel } from "@/components/hive/dataset-recipe-wizard-panel";
import { LocalAdapterRegistryPanel } from "@/components/hive/local-adapter-registry-panel";
import { SovereignRecipeHintsPanel } from "@/components/hive/sovereign-recipe-hints-panel";
import { LocalFinetuneQueuePanel } from "@/components/hive/local-finetune-queue-panel";
import { LocalInferencePanel } from "@/components/hive/local-inference-panel";
import { VerifiedDatasetExportPanel } from "@/components/hive/verified-dataset-export-panel";
import { QsSelect } from "@/components/ui/qs-select";
import { InfoHint } from "@/components/hive/info-hint";
import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveDelete, hiveGet, hivePatchJson, hivePostJson, hivePutJson } from "@/lib/api";
import type { LlmKeyMaskRow } from "@/lib/hive-types";
import { localizeDescription } from "@/lib/ui-copy";
import { cn } from "@/lib/utils";

type ProviderId = "grok" | "anthropic" | "openai" | "openrouter" | "deepgram" | "elevenlabs";
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

const PROVIDERS: ProviderId[] = ["grok", "anthropic", "openai", "openrouter", "deepgram", "elevenlabs"];

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
    hint: {
      en: "Optional fallback — factory and agents use your primary provider (Nemotron when marked primary).",
      sk: "Volitelny fallback — factory a agenti pouzivaju primarneho providera (Nemotron ak je primary).",
    },
  },
  anthropic: {
    title: { en: "Claude - Anthropic", sk: "Claude - Anthropic" },
    hint: {
      en: "Optional fallback only — not required when Grok is your primary provider.",
      sk: "Volitelny fallback — nie je potrebny ak pouzivas Grok.",
    },
  },
  openai: {
    title: { en: "OpenAI - GPT-4o mini", sk: "OpenAI - GPT-4o mini" },
    hint: {
      en: "Optional tertiary fallback — Skill Factory follows WORKFLOW_BREAKER_* env chain (Nemotron primary in prod).",
      sk: "Volitelny terciarny fallback — Skill Factory ide cez WORKFLOW_BREAKER_* retazec.",
    },
  },
  openrouter: {
    title: { en: "OpenRouter - NVIDIA Nemotron", sk: "OpenRouter - NVIDIA Nemotron" },
    hint: {
      en: "Primary for factory + agents when marked primary. Default: nvidia/nemotron-3-ultra-550b-a55b:free.",
      sk: "Primary pre factory + agentov ak je oznaceny primary. Default: nvidia/nemotron-3-ultra-550b-a55b:free.",
    },
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
  openrouter: {
    logo: "OR",
    bgColor: "#150f24",
    borderColor: "rgb(255 0 170 / 0.32)",
    textColor: "#FF00AA",
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

interface LlmProviderCollapsibleProps {
  readonly provider: ProviderId;
  readonly title: string;
  readonly hint: string;
  readonly open: boolean;
  readonly onToggle: () => void;
  readonly masked?: LlmKeyMaskRow;
  readonly isPrimary: boolean;
  readonly headerActions: ReactNode;
  readonly children: ReactNode;
}

/** Collapsed LLM shard tab — expands to full credential form (hierarchy-style). */
function LlmProviderCollapsible({
  provider,
  title,
  hint,
  open,
  onToggle,
  masked,
  isPrimary,
  headerActions,
  children,
}: LlmProviderCollapsibleProps): JSX.Element {
  const skin = PROVIDER_SKINS[provider];

  return (
    <section
      className={cn("v4-card v4-card-tight v4-llm-provider-panel overflow-hidden", open && "v4-llm-provider-panel--open")}
      style={
        {
          borderColor: skin.borderColor,
          "--v4-llm-panel-border": skin.borderColor,
        } as CSSProperties
      }
    >
      <button
        type="button"
        className="v4-panel-collapsible-trigger flex w-full min-w-0 items-center justify-between gap-3 py-2.5 text-left"
        onClick={onToggle}
        aria-expanded={open}
        aria-controls={`llm-provider-panel-${provider}`}
      >
        <span className="flex min-w-0 items-center gap-3">
          <span
            className="v4-provider-logo shrink-0"
            style={{
              background: skin.bgColor,
              border: `1px solid ${skin.borderColor}`,
              color: skin.textColor,
            }}
          >
            {skin.logo}
          </span>
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold text-(--qs-text-1)" role="heading" aria-level={3}>
              {title}
            </span>
            <span className="hidden truncate text-xs text-(--qs-text-3) sm:block">{hint}</span>
          </span>
        </span>
        <span className="flex shrink-0 items-center gap-3">
          {isPrimary ? <V4Badge tone="gold">primary</V4Badge> : null}
          {masked?.api_key_masked ? <V4Badge tone="gold">vault</V4Badge> : <V4Badge tone="info">empty</V4Badge>}
          <span
            className={cn("v4-panel-collapsible-chevron", open && "v4-panel-collapsible-chevron--open")}
            aria-hidden
          >
            <ChevronDown className="h-4 w-4" />
          </span>
        </span>
      </button>

      {open ? (
        <div id={`llm-provider-panel-${provider}`} className="border-t pt-4" style={{ borderColor: skin.borderColor }}>
          <div className="mb-4 flex flex-wrap items-start justify-end gap-2">{headerActions}</div>
          {children}
        </div>
      ) : null}
    </section>
  );
}

export function SettingsLlmKeysPanel() {
  const { language } = useUiLanguage();
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
    openrouter: "",
    deepgram: "",
    elevenlabs: "",
  });
  const [labels, setLabels] = useState<Record<string, string>>({
    grok: "",
    anthropic: "",
    openai: "",
    openrouter: "",
    deepgram: "",
    elevenlabs: "",
  });
  const [primaryFlags, setPrimaryFlags] = useState<Record<string, boolean>>({
    grok: true,
    anthropic: false,
    openai: false,
    openrouter: false,
    deepgram: false,
    elevenlabs: false,
  });
  const [testMsg, setTestMsg] = useState<Record<string, string>>({});
  const [openProviders, setOpenProviders] = useState<Record<ProviderId, boolean>>({
    grok: false,
    anthropic: false,
    openai: false,
    openrouter: false,
    deepgram: false,
    elevenlabs: false,
  });

  function toggleProvider(provider: ProviderId): void {
    setOpenProviders((prev) => ({ ...prev, [provider]: !prev[provider] }));
  }

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
        openrouter: "",
        deepgram: "",
        elevenlabs: "",
      };
      const nextPrimary: Record<string, boolean> = {
        grok: true,
        anthropic: false,
        openai: false,
        openrouter: false,
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
      toast.success("Provider metadata saved.");
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
      await hivePostJson("llm-keys", {
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
      const responseText = (res.response ?? "ping ok").trim();
      const line = ok
        ? responseText.toUpperCase() === "CONNECTED"
          ? "✅ CONNECTED"
          : `✅ CONNECTED (${responseText})`
        : `❌ ${res.error ?? "ping failed"}`;
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
      toast.success("Voice preferences saved.");
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

      <CostGuardianRoutingPanel />
      <LocalInferencePanel />
      <VerifiedDatasetExportPanel />
      <DatasetRecipeWizardPanel />
      <LocalAdapterRegistryPanel />
      <SovereignRecipeHintsPanel />
      <LocalFinetuneQueuePanel />

      <V4Card className="v4-voice-prefs-card">
        <V4CardHeader
          as="h3"
          title="Preferred voice provider (STT/TTS)"
          description={localizeDescription(language, {
            en: "STT/TTS priority, latency, and voice profile for Ballroom voice chat.",
            sk: "Priorita STT/TTS, latencia a hlas pre Ballroom voice chat.",
          })}
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
        <div className="v4-voice-prefs-body">
          <section className="v4-voice-prefs-section" aria-label="Pipeline">
            <p className="v4-voice-prefs-section-label">Pipeline</p>
            <div className="v4-voice-prefs-grid">
              <label className="v4-voice-prefs-field">
                <span className="qs-label">STT priority</span>
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
              <label className="v4-voice-prefs-field">
                <span className="qs-label">TTS priority</span>
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
              <label className="v4-voice-prefs-field">
                <span className="qs-label">Response mode</span>
                <QsSelect
                  value={voicePrefs.latency_mode}
                  disabled={voicePrefsBusy}
                  onValueChange={(next) =>
                    setVoicePrefs((prev) => ({
                      ...prev,
                      latency_mode: next as "balanced" | "fast",
                    }))
                  }
                  options={[...LATENCY_MODE_OPTIONS]}
                />
              </label>
            </div>
          </section>

          <section className="v4-voice-prefs-section" aria-label="Voice detection">
            <p className="v4-voice-prefs-section-label">Voice detection</p>
            <div className="v4-voice-prefs-grid">
              <label className="v4-voice-prefs-field">
                <span className="qs-label">VAD threshold</span>
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
                  className="v4-voice-prefs-range"
                />
                <p className="v4-voice-prefs-hint">
                  Voice sensitivity: {voicePrefs.vad_threshold.toFixed(2)}
                </p>
              </label>
              <label className="v4-voice-prefs-field">
                <span className="qs-label">Silence duration (ms)</span>
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
              <label className="v4-voice-prefs-field">
                <span className="qs-label">Voice language</span>
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
          </section>

          <section className="v4-voice-prefs-section" aria-label="Voice output">
            <p className="v4-voice-prefs-section-label">Voice output</p>
            <div className="v4-voice-prefs-grid v4-voice-prefs-grid--voice-output">
              <label className="v4-voice-prefs-field">
                <span className="qs-label">Voice profile</span>
                <QsSelect
                  value={voicePrefs.tts_voice_id}
                  disabled={voicePrefsBusy}
                  onValueChange={(next) =>
                    setVoicePrefs((prev) => ({
                      ...prev,
                      tts_voice_id: next,
                    }))
                  }
                  options={[...VOICE_PROFILE_OPTIONS]}
                />
              </label>
              <label className="v4-voice-prefs-field">
                <span className="qs-label">Voice tone</span>
                <QsSelect
                  value={voicePrefs.tts_tone}
                  disabled={voicePrefsBusy}
                  onValueChange={(next) =>
                    setVoicePrefs((prev) => ({
                      ...prev,
                      tts_tone: next,
                    }))
                  }
                  options={[...VOICE_TONE_OPTIONS]}
                />
              </label>
            </div>
          </section>
        </div>
        <div className="v4-voice-prefs-footer">
          <button
            type="button"
            disabled={voicePrefsBusy}
            onClick={() => void saveVoicePreferences()}
            className="qs-btn qs-btn--primary v4-voice-prefs-save"
          >
            Save voice preferences
          </button>
        </div>
      </V4Card>

      <div className="flex flex-col gap-3">
        {PROVIDERS.map((provider) => {
          const masked = rowFor(provider);
          const copy = PROVIDER_COPY[provider];
          const title = copy.title.en;
          const hint = localizeDescription(language, copy.hint);
          return (
            <LlmProviderCollapsible
              key={provider}
              provider={provider}
              title={title}
              hint={hint}
              open={openProviders[provider]}
              onToggle={() => toggleProvider(provider)}
              masked={masked}
              isPrimary={Boolean(primaryFlags[provider])}
              headerActions={
                <>
                  <button type="button" disabled={busy} onClick={() => void testProvider(provider)} className="qs-btn qs-btn--ghost qs-btn--sm">
                    Test
                  </button>
                  <button type="button" disabled={busy || !masked} onClick={() => void clearProvider(provider)} className="qs-btn qs-btn--ghost qs-btn--sm text-danger">
                    Remove
                  </button>
                </>
              }
            >
              <div className="v4-section-header-row mb-4">
                <div className="min-w-0 flex-1">
                  <h3>{title}</h3>
                  <p className="desc">{hint}</p>
                </div>
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
                  Primary shard for this provider
                </label>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void saveProviderMeta(provider)}
                  className="qs-btn qs-btn--ghost qs-btn--sm mt-2"
                >
                  Save label
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
            </LlmProviderCollapsible>
          );
        })}
      </div>
    </div>
  );
}
