"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hiveDelete, hiveGet, hivePostJson } from "@/lib/api";
import type { ApiKeyCreated, ApiKeyListItem } from "@/lib/hive-dashboard-session";

/** Must match ``_MAX_ACTIVE_API_KEYS_PER_OPERATOR`` on the API. */
const MAX_ACTIVE_API_KEY_SLOTS = 50;

function formatCreatedSk(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return "—";
  }
  return d.toLocaleDateString("sk-SK", { year: "numeric", month: "2-digit", day: "2-digit" });
}

function formatLastUsedSk(iso: string | null): string {
  if (!iso) {
    return "nikdy";
  }
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms) || ms < 0) {
    return "—";
  }
  const sec = Math.floor(ms / 1000);
  if (sec < 15) {
    return "práve teraz";
  }
  if (sec < 60) {
    return `pred ${sec}s`;
  }
  const min = Math.floor(sec / 60);
  if (min < 60) {
    return min === 1 ? "pred 1 min" : `pred ${min} min`;
  }
  const h = Math.floor(min / 60);
  if (h < 48) {
    return h === 1 ? "pred 1 h" : `pred ${h} h`;
  }
  const days = Math.floor(h / 24);
  return days === 1 ? "pred 1 dňom" : `pred ${days} dňami`;
}

/** Client-side sanity check aligned with backend ``normalize_api_key_source_name``. */
function sourceSlugHint(raw: string): string | null {
  const slug = raw
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "");
  if (slug.length < 2) {
    return "Názov zdroja je príliš krátky (aspoň 2 znaky po normalizácii).";
  }
  if (slug.length > 64) {
    return "Názov zdroja je príliš dlhý.";
  }
  if (!/^[a-z0-9]+(?:[_-][a-z0-9]+)*$/.test(slug)) {
    return "Povolené: malé písmená, čísla, jednoduché _ alebo - (napr. ci_staging, vscode-extension).";
  }
  return null;
}

export function SettingsApiKeysPanel() {
  const [rows, setRows] = useState<ApiKeyListItem[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [newSourceName, setNewSourceName] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [minted, setMinted] = useState<ApiKeyCreated | null>(null);

  const load = useCallback(async () => {
    try {
      const list = await hiveGet<ApiKeyListItem[]>("auth/api-keys");
      setRows(list);
      setErr(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Načítanie zlyhalo";
      setErr(msg);
      setRows(null);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function createKey(): Promise<void> {
    const hint = sourceSlugHint(newSourceName);
    if (hint) {
      toast.error(hint);
      return;
    }
    setBusy(true);
    try {
      const created = await hivePostJson<ApiKeyCreated>("auth/api-keys", {
        source_name: newSourceName.trim(),
        label: newLabel.trim() || null,
      });
      setMinted(created);
      setCreateOpen(false);
      setNewSourceName("");
      setNewLabel("");
      await load();
      toast.success("Nový kľúč vytvorený — ulož plaintext, zobrazí sa len raz.");
    } catch (e) {
      if (e instanceof HiveApiError) {
        if (e.status === 409) {
          toast.error("Aktívny kľúč pre tento názov zdroja už existuje — zvoľ iný slug.");
          return;
        }
        if (e.status === 422) {
          if (String(e.message).toLowerCase().includes("maximum")) {
            toast.error(`Dosiahnutý limit ${String(MAX_ACTIVE_API_KEY_SLOTS)} aktívnych kľúčov — jeden zruš a skús znova.`);
            return;
          }
          toast.error(e.message || "Neplatný názov zdroja alebo vstup.");
          return;
        }
      }
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Vytvorenie zlyhalo";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function revoke(id: string): Promise<void> {
    if (!window.confirm("Naozaj zrušiť tento API kľúč? Skripty s ním prestanú fungovať.")) {
      return;
    }
    setBusy(true);
    try {
      await hiveDelete<void>(`auth/api-keys/${id}`);
      await load();
      toast.success("Kľúč bol zrušený.");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Zrušenie zlyhalo";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  function copyPlaintext(): void {
    if (!minted) {
      return;
    }
    void navigator.clipboard.writeText(minted.plaintext);
    toast.message("Skopírované do schránky.");
  }

  if (err && !rows) {
    return (
      <div className="rounded-3xl border border-danger/30 bg-danger/[0.06] p-6 text-sm text-danger">
        API kľúče: {err}
      </div>
    );
  }

  if (!rows) {
    return <div className="h-64 animate-pulse rounded-3xl bg-white/[0.04]" />;
  }

  const slotsUsed = rows.length;
  const atLimit = slotsUsed >= MAX_ACTIVE_API_KEY_SLOTS;

  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-3xl border border-white/[0.08] bg-[#0c0c14]/95 p-6 md:p-7">
        <h2 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">API keys</h2>
        <p className="mt-1 font-[family-name:var(--font-inter)] text-sm text-zinc-500">
          Sloty pre externé zdroje informácií (skripty, integrácie, partner API). Aktívnych kľúčov:{' '}
          <span className="font-semibold text-pollen">
            {slotsUsed}/{MAX_ACTIVE_API_KEY_SLOTS}
          </span>
          . Každý slot má unikátny <span className="text-zinc-400">názov zdroja</span> (slug); bearer token vidíš len pri
          vytvorení.
        </p>

        <ul className="mt-6 divide-y divide-white/[0.06] border-t border-white/[0.06]">
          {rows.length === 0 ? (
            <li className="py-8 text-center font-[family-name:var(--font-inter)] text-sm text-zinc-500">Zatiaľ žiadne kľúče.</li>
          ) : (
            rows.map((row) => (
              <li key={row.id} className="flex flex-col gap-2 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-baseline gap-2 gap-y-1">
                    <span className="rounded-md border border-cyan/30 bg-cyan/[0.08] px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-xs font-semibold text-cyan">
                      {row.source_name ?? "— legacy"}
                    </span>
                    <p className="font-[family-name:var(--font-jetbrains-mono)] text-sm font-semibold text-[#fafafa]">{row.masked_prefix}</p>
                  </div>
                  <p className="mt-1 font-[family-name:var(--font-inter)] text-xs text-zinc-500">
                    Vytvorené {formatCreatedSk(row.created_at)} · naposledy {formatLastUsedSk(row.last_used_at)}
                    {row.label ? ` · poznámka: ${row.label}` : ""}
                  </p>
                </div>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void revoke(row.id)}
                  className="shrink-0 rounded-full border border-white/20 bg-black/50 px-4 py-2 font-[family-name:var(--font-inter)] text-xs font-semibold text-zinc-200 transition hover:border-danger/40 hover:text-danger disabled:opacity-40"
                >
                  Zrušiť
                </button>
              </li>
            ))
          )}
        </ul>

        <button
          type="button"
          disabled={busy || atLimit}
          onClick={() => {
            setNewSourceName("");
            setNewLabel("");
            setCreateOpen(true);
          }}
          title={atLimit ? `Maximum ${String(MAX_ACTIVE_API_KEY_SLOTS)} aktívnych kľúčov` : undefined}
          className="mt-6 w-full rounded-2xl border border-pollen/50 bg-pollen py-3 font-[family-name:var(--font-inter)] text-sm font-bold text-black shadow-[0_0_24px_rgb(255_184_0/0.35)] transition hover:brightness-110 disabled:opacity-40 sm:w-auto sm:px-8"
        >
          {atLimit ? `Limit ${String(MAX_ACTIVE_API_KEY_SLOTS)} slotov` : "+ Nový kľúč"}
        </button>
      </section>

      {createOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" role="dialog" aria-modal>
          <div className="w-full max-w-md rounded-3xl border border-white/10 bg-[#0a0a12] p-6 shadow-[0_0_48px_rgb(255_184_0/0.12)]">
            <h3 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">Nový API kľúč</h3>
            <p className="mt-2 text-sm text-zinc-500">
              <span className="font-semibold text-zinc-400">Názov zdroja</span> je identifikátor integrácie (jednotný slug pre tento účet).
              Používajú ho logy backendu aj zobrazenie v dashboarde; duplicitný aktívny zdroj nie je povolený.
            </p>
            <label className="mt-5 block font-[family-name:var(--font-inter)] text-xs font-semibold uppercase tracking-wide text-zinc-500">
              Názov zdroja (slug)
              <input
                type="text"
                autoComplete="off"
                spellCheck={false}
                value={newSourceName}
                onChange={(e) => setNewSourceName(e.target.value)}
                placeholder="napr. ci_main, vscode_ext, zakaznik_xyz"
                className="mt-1.5 w-full rounded-xl border border-white/15 bg-black/50 px-3 py-2.5 font-[family-name:var(--font-jetbrains-mono)] text-sm text-[#fafafa] outline-none focus:border-pollen/40"
              />
            </label>
            <label className="mt-4 block font-[family-name:var(--font-inter)] text-xs font-semibold uppercase tracking-wide text-zinc-500">
              Poznámka (voliteľná)
              <input
                type="text"
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
                placeholder="ľudsky čitateľný popis iba pre teba"
                className="mt-1.5 w-full rounded-xl border border-white/15 bg-black/50 px-3 py-2.5 text-sm text-[#fafafa] outline-none focus:border-pollen/40"
              />
            </label>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-xl px-4 py-2 text-sm text-zinc-400 hover:text-[#fafafa]"
                onClick={() => setCreateOpen(false)}
              >
                Zrušiť
              </button>
              <button
                type="button"
                disabled={busy}
                className="rounded-xl border border-pollen bg-pollen px-4 py-2 text-sm font-bold text-black shadow-[0_0_20px_rgb(255_184_0/0.35)] disabled:opacity-40"
                onClick={() => void createKey()}
              >
                Vytvoriť
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {minted ? (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/75 p-4" role="dialog" aria-modal>
          <div className="w-full max-w-lg rounded-3xl border border-pollen/35 bg-[#0a0a12] p-6">
            <h3 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-pollen">Ulož si kľúč</h3>
            <p className="mt-2 text-sm text-zinc-400">
              Plaintext token sa už nezobrazí. Používaj hlavičku <span className="font-mono text-zinc-300">Authorization: Bearer …</span> s hodnotou
              nižšie.
            </p>
            <p className="mt-4 font-[family-name:var(--font-inter)] text-xs text-zinc-500">
              Názov zdroja:&nbsp;
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-sm font-semibold text-cyan">
                {minted.source_name ?? "—"}
              </span>
            </p>
            <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-all rounded-xl border border-white/10 bg-black/50 p-3 font-[family-name:var(--font-jetbrains-mono)] text-xs text-[#fafafa]">
              {minted.plaintext}
            </pre>
            <div className="mt-6 flex flex-wrap gap-2">
              <button
                type="button"
                className="rounded-xl border border-cyan/30 px-4 py-2 text-sm font-semibold text-cyan"
                onClick={() => copyPlaintext()}
              >
                Kopírovať
              </button>
              <button
                type="button"
                className="rounded-xl bg-pollen px-4 py-2 text-sm font-bold text-black"
                onClick={() => setMinted(null)}
              >
                Uložil som ho
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
