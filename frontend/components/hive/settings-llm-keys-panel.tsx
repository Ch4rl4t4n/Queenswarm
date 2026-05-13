"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hiveDelete, hiveGet, hivePostJson } from "@/lib/api";
import type { LlmKeyMaskRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

const PROVIDERS: { id: "grok" | "anthropic" | "openai"; title: string; hint: string }[] = [
  { id: "grok", title: "Grok (xAI)", hint: "Primary routing — persisted in hive vault." },
  { id: "anthropic", title: "Claude · Anthropic", hint: "Admin-only upsert unless env already supplies credential." },
  { id: "openai", title: "OpenAI · GPT‑4o mini", hint: "Cheap simulations / parity checks." },
];

const PROVIDER_SKINS: Record<
  "grok" | "anthropic" | "openai",
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
};

export function SettingsLlmKeysPanel() {
  const [keys, setKeys] = useState<LlmKeyMaskRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [inputs, setInputs] = useState<Record<string, string>>({ grok: "", anthropic: "", openai: "" });
  const [labels, setLabels] = useState<Record<string, string>>({
    grok: "Primary",
    anthropic: "Primary",
    openai: "Primary",
  });
  const [testMsg, setTestMsg] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    try {
      const rows = await hiveGet<{ keys: LlmKeyMaskRow[] }>("llm-keys");
      setKeys(rows.keys ?? []);
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

  async function save(provider: "grok" | "anthropic" | "openai"): Promise<void> {
    const trimmed = inputs[provider]?.trim() ?? "";
    if (trimmed.length < 12) {
      toast.error("Paste a complete API secret (minimum 12 characters).");
      return;
    }
    setBusy(true);
    try {
      await hivePostJson("llm-keys/", {
        provider,
        label: labels[provider]?.trim() || `${provider.toUpperCase()} vault`,
        api_key: trimmed,
        is_primary: true,
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

  async function clearProvider(provider: "grok" | "anthropic" | "openai"): Promise<void> {
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

  async function testProvider(provider: "grok" | "anthropic" | "openai"): Promise<void> {
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

  if (err && keys.length === 0) {
    return (
      <div className="qs-settings-card border-[var(--qs-red)]/30 bg-[var(--qs-red)]/[0.06] text-[var(--qs-red)]">
        LLM keys: {err}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-[var(--qs-gap)]">
      <p className="font-[family-name:var(--font-inter)] text-sm text-[var(--qs-text-3)]">
        Credentials call{" "}
        <span className="font-mono text-xs text-[var(--qs-cyan)]">POST /api/v1/llm-keys</span> through the hive proxy · masked
        values never round-trip plaintext.
      </p>

      <div className="flex flex-col gap-0">
        {PROVIDERS.map(({ id: provider, title, hint }) => {
          const masked = rowFor(provider);
          const skin = PROVIDER_SKINS[provider];
          return (
            <article key={provider} className="qs-settings-card">
              <header className="qs-settings-card__header">
                <div className="flex min-w-0 items-center gap-3">
                  <div
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--qs-radius-sm)] text-[11px] font-bold"
                    style={{
                      background: skin.bgColor,
                      border: `1px solid ${skin.borderColor}`,
                      color: skin.textColor,
                    }}
                  >
                    {skin.logo}
                  </div>
                  <div className="min-w-0">
                    <div className="qs-settings-card__title">{title}</div>
                    <div className="qs-settings-card__subtitle">{hint}</div>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void testProvider(provider)}
                    className="qs-btn qs-btn--cyan qs-btn--sm"
                  >
                    Test
                  </button>
                  <button
                    type="button"
                    disabled={busy || !masked}
                    onClick={() => void clearProvider(provider)}
                    className="qs-btn qs-btn--danger qs-btn--sm"
                  >
                    Remove
                  </button>
                </div>
              </header>

              <div className="mb-3">
                <label className="qs-label" htmlFor={`llm-label-${provider}`}>
                  Friendly label
                </label>
                <input
                  id={`llm-label-${provider}`}
                  type="text"
                  value={labels[provider] ?? ""}
                  disabled={busy}
                  onChange={(e) => setLabels((prev) => ({ ...prev, [provider]: e.target.value }))}
                  className="qs-input"
                />
              </div>

              {masked?.api_key_masked ? (
                <p className="mb-3 font-mono text-[12px] text-[var(--qs-amber)]">Saved secret {masked.api_key_masked}</p>
              ) : (
                <p className="mb-3 font-mono text-[11px] text-[var(--qs-text-3)]">No credential stored for this shard.</p>
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
                    testMsg[provider].startsWith("✅") ? "text-[var(--qs-green)]" : "text-[var(--qs-red)]",
                  )}
                >
                  {testMsg[provider]}
                </p>
              ) : null}
            </article>
          );
        })}
      </div>
    </div>
  );
}
