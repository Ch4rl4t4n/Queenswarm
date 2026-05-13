"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hiveDelete, hiveGet, hivePostJson } from "@/lib/api";
import type { DashboardOperatorMe, LlmProvidersStatus } from "@/lib/hive-dashboard-session";

type LlmProviderId = "grok" | "anthropic" | "openai";

interface PlannedProviderMeta {
  id: Exclude<LlmProviderId, "grok">;
  title: string;
  note: string;
  borderClass: string;
  textClass: string;
  dotClass: string;
}

const PLANNED_PROVIDERS: PlannedProviderMeta[] = [
  {
    id: "anthropic",
    title: "Claude (Anthropic)",
    note: "Záložný model — rozšírime UI neskôr; zatiaľ nastav cez env na API serveri.",
    borderClass: "border-pollen/35",
    textClass: "text-pollen",
    dotClass: "bg-pollen shadow-[0_0_6px_rgb(255_184_0/0.6)]",
  },
  {
    id: "openai",
    title: "OpenAI · GPT-4o-mini",
    note: "Simulácie / lacný fallback — rozšírime UI neskôr; zatiaľ env.",
    borderClass: "border-cyan/35",
    textClass: "text-cyan",
    dotClass: "bg-cyan shadow-[0_0_6px_rgb(0_255_255/0.6)]",
  },
];

function configuredForProvider(status: LlmProvidersStatus | null, id: LlmProviderId): boolean {
  if (!status) {
    return false;
  }
  if (id === "grok") {
    return status.grok_configured;
  }
  if (id === "anthropic") {
    return status.anthropic_configured;
  }
  return status.openai_configured;
}

function fromVaultForProvider(status: LlmProvidersStatus | null, id: LlmProviderId): boolean {
  if (!status) {
    return false;
  }
  if (id === "grok") {
    return status.grok_from_vault;
  }
  if (id === "anthropic") {
    return status.anthropic_from_vault;
  }
  return status.openai_from_vault;
}

export function SettingsLlmKeysPanel() {
  const [me, setMe] = useState<DashboardOperatorMe | null>(null);
  const [status, setStatus] = useState<LlmProvidersStatus | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [grokKeyInput, setGrokKeyInput] = useState("");

  const load = useCallback(async () => {
    try {
      const [m, s] = await Promise.all([
        hiveGet<DashboardOperatorMe>("auth/me"),
        hiveGet<LlmProvidersStatus>("auth/integrations/llm-providers"),
      ]);
      setMe(m);
      setStatus(s);
      setErr(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Načítanie zlyhalo";
      setErr(msg);
      setMe(null);
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function saveGrokKey(): Promise<void> {
    const trimmed = grokKeyInput.trim();
    if (trimmed.length < 12) {
      toast.error("Zadaj platný xAI Grok API kľúč (min. 12 znakov).");
      return;
    }
    setBusy(true);
    try {
      await hivePostJson<{ ok: boolean }>("auth/integrations/llm-providers/grok/secret", {
        api_key: trimmed,
      });
      setGrokKeyInput("");
      await load();
      toast.success("Grok kľúč bol uložený šifrovane do trezora (override namiesto env na tomto API processe).");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Uloženie zlyhalo";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function clearGrokVault(): Promise<void> {
    if (!window.confirm("Odstrániť Grok override z trezora a vrátiť sa k premenným prostredia?")) {
      return;
    }
    setBusy(true);
    try {
      await hiveDelete<void>("auth/integrations/llm-providers/grok/secret");
      await load();
      toast.success("Trezor vymazaný — ak je nastavené, platí env.");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Zlyhalo";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  if (err && !me) {
    return (
      <div className="rounded-3xl border border-danger/30 bg-danger/[0.06] p-6 text-sm text-danger">
        LLM kľúče: {err}
      </div>
    );
  }

  if (!me || !status) {
    return <div className="h-64 animate-pulse rounded-3xl bg-white/[0.04]" />;
  }

  const grokOk = configuredForProvider(status, "grok");
  const grokVault = fromVaultForProvider(status, "grok");

  return (
    <div className="flex flex-col gap-8">
      <section className="rounded-3xl border border-white/[0.08] bg-[#0c0c14]/95 p-6 md:p-7">
        <h2 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">
          Grok (xAI) — primárny LLM
        </h2>
        <p className="mt-1 font-[family-name:var(--font-inter)] text-sm text-zinc-500">
          Tu vložíš svoj xAI Grok API kľúč; backend ho uloží do trezora, LiteLLM ho rozpozná ako primárny routing a zobrazený stav tu sa podľa toho aktualizuje.
        </p>

        <div className="mt-5 rounded-2xl border border-success/25 bg-black/35 p-4 md:p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="font-[family-name:var(--font-inter)] text-sm font-semibold text-[#fafafa]">Stav Grok</p>
              <p className="mt-0.5 font-[family-name:var(--font-inter)] text-xs text-zinc-500">
                {grokVault ? "Zdroj · trezor (dashboard)" : "Zdroj · premenné prostredia na workeri"}
              </p>
            </div>
            <div className="shrink-0">
              {grokOk ? (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-success/35 bg-black/40 px-2.5 py-1 font-[family-name:var(--font-inter)] text-xs font-medium text-success">
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-success shadow-[0_0_6px_rgb(0_255_136/0.9)]" />
                  Pripojené
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-alert/35 bg-black/40 px-2.5 py-1 font-[family-name:var(--font-inter)] text-xs font-medium text-alert">
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-alert shadow-[0_0_6px_rgb(255_0_170/0.7)]" />
                  Chýba kľúč
                </span>
              )}
            </div>
          </div>

          <label htmlFor="grok-api-key" className="sr-only">
            Grok API kľúč
          </label>
          <input
            id="grok-api-key"
            type="password"
            value={grokKeyInput}
            onChange={(e) => setGrokKeyInput(e.target.value)}
            autoComplete="off"
            spellCheck={false}
            disabled={busy}
            className="mt-5 w-full rounded-xl border border-white/15 bg-black/55 px-3 py-3 font-[family-name:var(--font-jetbrains-mono)] text-sm text-[#fafafa] outline-none focus:border-success/45"
            placeholder="xai-… alebo vlastný Grok secret"
          />
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => void saveGrokKey()}
              className="rounded-full border border-pollen bg-pollen px-4 py-2.5 font-[family-name:var(--font-inter)] text-xs font-bold text-black shadow-[0_0_20px_rgb(255_184_0/0.25)] transition hover:bg-[#ffc933] disabled:opacity-40"
            >
              Uložiť kľúč
            </button>
            {grokVault ? (
              <button
                type="button"
                disabled={busy}
                onClick={() => void clearGrokVault()}
                className="rounded-full border border-white/18 bg-black/50 px-4 py-2.5 font-[family-name:var(--font-inter)] text-xs font-semibold text-zinc-300 transition hover:border-zinc-500 hover:text-zinc-100 disabled:opacity-40"
              >
                Odstrániť z trezora
              </button>
            ) : null}
          </div>
          <p className="mt-3 font-[family-name:var(--font-inter)] text-[11px] leading-relaxed text-zinc-600">
            Hodnotu v inpute nikdy neukladáme do logov. Worker procesy môžu potrebovať reštart, kým použijú nový záznam
            trezora.
          </p>
        </div>
      </section>

      <section className="rounded-3xl border border-white/[0.06] bg-[#08080f]/95 p-6 md:p-7">
        <h2 className="font-[family-name:var(--font-space-grotesk)] text-base font-semibold text-zinc-300">
          Ďalší poskytovatelia — zatiaľ len načítanie stavu
        </h2>
        <p className="mt-1 font-[family-name:var(--font-inter)] text-xs text-zinc-600">
          UI na zadanie kľúča pridáme neskôr; zatiaľ ich nastavuješ cez prostredie na serveri. Nižšie vidíš, či systém už
          eviduje funkčný kľúč.
        </p>
        <ul className="mt-5 divide-y divide-white/[0.06] border-t border-white/[0.06]">
          {PLANNED_PROVIDERS.map((row) => {
            const ok = configuredForProvider(status, row.id);
            const vault = fromVaultForProvider(status, row.id);
            return (
              <li key={row.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="font-[family-name:var(--font-inter)] text-sm font-semibold text-zinc-200">{row.title}</p>
                  <p className="mt-1 font-[family-name:var(--font-inter)] text-xs text-zinc-500">{row.note}</p>
                  <div className="mt-2">
                    {ok ? (
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full border bg-black/40 px-2.5 py-0.5 font-[family-name:var(--font-inter)] text-[11px] font-medium opacity-95 ${row.borderClass} ${row.textClass}`}
                      >
                        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${row.dotClass}`} />
                        Pripojené {vault ? "· trezor" : "· env"}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-black/40 px-2.5 py-0.5 font-[family-name:var(--font-inter)] text-[11px] font-medium text-zinc-500">
                        Neskonfigurované (env prázdny)
                      </span>
                    )}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
