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
      <div className="rounded-3xl border border-danger/30 bg-danger/[0.06] p-6 text-sm text-danger">
        LLM keys: {err}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <p className="font-[family-name:var(--font-inter)] text-sm text-zinc-500">
        Credentials call <span className="font-mono text-xs text-data">POST /api/v1/llm-keys</span> through the hive proxy · masked values never round-trip plaintext.
      </p>
      <div className="grid gap-6">
        {PROVIDERS.map(({ id: provider, title, hint }) => {
          const masked = rowFor(provider);
          return (
            <section
              key={provider}
              className="rounded-3xl border border-white/[0.08] bg-[#0c0c14]/95 p-6 md:p-7"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">{title}</h2>
                  <p className="mt-1 font-[family-name:var(--font-inter)] text-sm text-zinc-500">{hint}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void testProvider(provider)}
                    className="rounded-full border border-cyan/35 px-4 py-2 text-xs font-semibold text-data hover:bg-cyan/10 disabled:opacity-40"
                  >
                    Test
                  </button>
                  <button
                    type="button"
                    disabled={busy || !masked}
                    onClick={() => void clearProvider(provider)}
                    className="rounded-full border border-danger/35 px-4 py-2 text-xs font-semibold text-danger hover:bg-danger/10 disabled:opacity-40"
                  >
                    Remove
                  </button>
                </div>
              </div>

              <label className="mt-5 block font-[family-name:var(--font-inter)] text-xs uppercase tracking-[0.12em] text-zinc-500">
                Friendly label
                <input
                  type="text"
                  value={labels[provider] ?? ""}
                  disabled={busy}
                  onChange={(e) => setLabels((prev) => ({ ...prev, [provider]: e.target.value }))}
                  className="mt-2 w-full rounded-xl border border-white/15 bg-black/55 px-3 py-2.5 font-[family-name:var(--font-inter)] text-sm text-[#fafafa]"
                />
              </label>

              {masked?.api_key_masked ? (
                <p className="mt-4 font-[family-name:var(--font-jetbrains-mono)] text-sm text-success">
                  Saved secret {masked.api_key_masked}
                </p>
              ) : (
                <p className="mt-4 font-[family-name:var(--font-inter)] text-xs text-zinc-500">No credential stored for this shard.</p>
              )}

              <label htmlFor={`llm-secret-${provider}`} className="sr-only">{title} secret</label>
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
                className="mt-3 w-full rounded-xl border border-white/15 bg-black/55 px-3 py-3 font-[family-name:var(--font-jetbrains-mono)] text-sm text-[#fafafa] outline-none focus:border-pollen/45 disabled:opacity-40"
              />
              <button
                type="button"
                disabled={busy}
                onClick={() => void save(provider)}
                className="mt-4 rounded-full border border-pollen bg-pollen px-5 py-2.5 text-xs font-bold text-black shadow-[0_0_18px_rgb(255_184_0/0.28)] hover:bg-[#ffc933] disabled:opacity-40"
              >
                Save key
              </button>
              {testMsg[provider] ? (
                <p className={cn("mt-3 font-[family-name:var(--font-jetbrains-mono)] text-xs", testMsg[provider].startsWith("✅") ? "text-success" : "text-danger")}>
                  {testMsg[provider]}
                </p>
              ) : null}
            </section>
          );
        })}
      </div>
    </div>
  );
}
