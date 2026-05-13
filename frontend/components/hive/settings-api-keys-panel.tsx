"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hiveDelete, hiveGet, hivePostJson } from "@/lib/api";
import type { ApiKeyCreated, ApiKeyListItem } from "@/lib/hive-dashboard-session";
import type { ExternalApiStoredRow, ExternalProviderMeta } from "@/lib/hive-types";

const MAX_SCRIPT_KEYS = 50;

/** Must match backend ``normalize_api_key_source_name``. */
function sourceSlugHint(raw: string): string | null {
  const slug = raw
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "");
  if (slug.length < 2) return "Slug too short.";
  if (slug.length > 64) return "Slug too long.";
  if (!/^[a-z0-9]+(?:[_-][a-z0-9]+)*$/.test(slug)) return "Alphanumeric + simple separators only.";
  return null;
}

function providerGlyph(id: string): string {
  return id.slice(0, 2).toUpperCase();
}

export function SettingsApiKeysPanel() {
  const [providers, setProviders] = useState<ExternalProviderMeta[]>([]);
  const [apis, setApis] = useState<ExternalApiStoredRow[]>([]);
  const [rows, setRows] = useState<ApiKeyListItem[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [selectedProvider, setSelectedProvider] = useState<string>("alpaca");
  const [credLabel, setCredLabel] = useState("");
  const [credJson, setCredJson] = useState("{}");

  const [createOpen, setCreateOpen] = useState(false);
  const [newSourceName, setNewSourceName] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [minted, setMinted] = useState<ApiKeyCreated | null>(null);

  const loadExternal = useCallback(async () => {
    const [catalog, stash] = await Promise.all([
      hiveGet<{ providers: ExternalProviderMeta[] }>("external-apis/providers"),
      hiveGet<{ apis: ExternalApiStoredRow[] }>("external-apis/"),
    ]);
    setProviders(catalog.providers ?? []);
    setApis(stash.apis ?? []);
  }, []);

  const loadScriptKeys = useCallback(async () => {
    const list = await hiveGet<ApiKeyListItem[]>("auth/api-keys");
    setRows(list);
  }, []);

  const loadAll = useCallback(async () => {
    try {
      await Promise.all([loadExternal(), loadScriptKeys()]);
      setErr(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Load failed";
      setErr(msg);
    }
  }, [loadExternal, loadScriptKeys]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  async function addExternalCred(): Promise<void> {
    if (!credLabel.trim()) {
      toast.error("Provide a memorable label.");
      return;
    }
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(credJson || "{}") as Record<string, unknown>;
    } catch {
      toast.error("Credentials JSON is invalid.");
      return;
    }
    setBusy(true);
    try {
      await hivePostJson("external-apis/", {
        provider: selectedProvider,
        label: credLabel.trim(),
        credentials: parsed,
      });
      setCredLabel("");
      setCredJson("{}");
      toast.success("External credential encrypted.");
      await loadExternal();
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Save failed";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function removeExternal(id: string): Promise<void> {
    setBusy(true);
    try {
      await hiveDelete(`external-apis/${id}`);
      toast.success("Credential removed.");
      await loadExternal();
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Delete failed";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function createScriptKey(): Promise<void> {
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
      await loadScriptKeys();
      toast.success("Minted scripted API key.");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Create failed";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function revokeScriptKey(id: string): Promise<void> {
    setBusy(true);
    try {
      await hiveDelete(`auth/api-keys/${id}`);
      await loadScriptKeys();
      toast.success("Script key revoked.");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Revoke failed";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  function copyPlaintext(): void {
    if (!minted) return;
    void navigator.clipboard.writeText(minted.plaintext);
    toast.message("Copied");
  }

  return (
    <div className="flex flex-col gap-10">
      {err ? (
        <p className="rounded-2xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">{err}</p>
      ) : null}

      <section className="rounded-3xl border border-white/[0.08] bg-[#0c0c14]/95 p-6 md:p-7">
        <h2 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">External data APIs</h2>
        <p className="mt-1 font-[family-name:var(--font-inter)] text-sm text-zinc-500">
          Encrypt JSON credential bundles per provider (Alpaca, Twitter/X, Yahoo, …). Keys never round-trip plaintext after save.
        </p>

        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {providers.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setSelectedProvider(p.id)}
              className={`rounded-2xl border px-4 py-4 text-left transition ${
                selectedProvider === p.id ? "border-pollen bg-pollen/[0.08]" : "border-white/10 bg-black/35 hover:border-cyan/30"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan/20 bg-black/55 font-[family-name:var(--font-jetbrains-mono)] text-xs font-bold text-pollen">
                  {providerGlyph(p.id)}
                </div>
                <div className="min-w-0">
                  <p className="truncate font-semibold text-[#fafafa]">{p.label}</p>
                  <p className="truncate font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase text-zinc-500">{p.id}</p>
                </div>
              </div>
              {selectedProvider === p.id ? <span className="mt-3 inline-block font-mono text-[10px] text-data">selected</span> : null}
            </button>
          ))}
        </div>

        <div className="mt-6 rounded-2xl border border-cyan/[0.12] bg-black/35 p-4">
          <label className="block text-xs uppercase tracking-[0.12em] text-zinc-500">
            Label for this credential
            <input
              value={credLabel}
              disabled={busy}
              onChange={(e) => setCredLabel(e.target.value)}
              className="mt-2 w-full rounded-xl border border-white/15 bg-black/55 px-3 py-2.5 text-sm text-[#fafafa]"
              placeholder={`${selectedProvider.toUpperCase()} trading desk`}
            />
          </label>
          <label className="mt-4 block text-xs uppercase tracking-[0.12em] text-zinc-500">
            Credentials JSON (`key_id`, `secret`, `bearer_token`, …)
            <textarea
              value={credJson}
              disabled={busy}
              onChange={(e) => setCredJson(e.target.value)}
              rows={5}
              className="mt-2 w-full rounded-xl border border-white/15 bg-black/55 px-3 py-2.5 font-mono text-xs text-[#fafafa]"
            />
          </label>
          <button
            type="button"
            disabled={busy}
            onClick={() => void addExternalCred()}
            className="mt-4 rounded-full border border-pollen bg-pollen px-5 py-2.5 text-xs font-bold text-black hover:bg-[#ffc933]"
          >
            Add encrypted key
          </button>
        </div>

        <div className="mt-8 space-y-3">
          <h3 className="font-[family-name:var(--font-space-grotesk)] text-sm font-semibold text-zinc-300">Stored bundles</h3>
          {apis.length === 0 ? (
            <p className="text-sm text-zinc-600">Nothing persisted yet.</p>
          ) : (
            apis.map((row) => (
              <div key={row.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/[0.07] bg-black/35 px-4 py-3">
                <div>
                  <p className="font-semibold text-[#fafafa]">{row.label}</p>
                  <p className="font-mono text-xs text-data">{row.provider}</p>
                  <pre className="mt-2 max-h-24 overflow-auto text-[10px] text-zinc-500">{JSON.stringify(row.credentials_masked, null, 2)}</pre>
                </div>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void removeExternal(row.id)}
                  className="rounded-full border border-danger/40 px-4 py-1.5 text-xs font-semibold text-danger hover:bg-danger/10 disabled:opacity-40"
                >
                  Remove
                </button>
              </div>
            ))
          )}
        </div>
      </section>

      <section className="rounded-3xl border border-white/[0.08] bg-[#0c0c14]/95 p-6 md:p-7">
        <h2 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">Hive script bearer keys</h2>
        <p className="mt-1 font-[family-name:var(--font-inter)] text-sm text-zinc-500">
          Mint dashboard-scoped bearer tokens for automation ({MAX_SCRIPT_KEYS} concurrent slots).
        </p>

        {!rows ? (
          <div className="mt-6 h-32 animate-pulse rounded-2xl bg-white/[0.04]" />
        ) : (
          <ul className="mt-6 divide-y divide-white/[0.06] border-t border-white/[0.06]">
            {rows.map((row) => (
              <li key={row.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-mono text-sm text-cyan">{row.source_name}</p>
                  <p className="text-xs text-zinc-500">{row.masked_prefix}</p>
                </div>
                <button type="button" disabled={busy} onClick={() => void revokeScriptKey(row.id)} className="rounded-full border px-4 py-1.5 text-xs text-danger">
                  Revoke
                </button>
              </li>
            ))}
          </ul>
        )}

        <button
          type="button"
          disabled={busy || (rows?.length ?? 0) >= MAX_SCRIPT_KEYS}
          onClick={() => setCreateOpen(true)}
          className="mt-6 rounded-2xl border border-pollen/60 bg-pollen px-6 py-3 text-xs font-black text-black hover:bg-[#ffc933]"
        >
          Mint script key
        </button>
      </section>

      {createOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4" role="dialog" aria-modal>
          <div className="w-full max-w-md rounded-3xl border border-white/10 bg-[#0a0a12] p-6">
            <h3 className="text-lg font-semibold text-[#fafafa]">New script slug</h3>
            <input
              placeholder="slug e.g. ci_main"
              value={newSourceName}
              disabled={busy}
              onChange={(e) => setNewSourceName(e.target.value)}
              className="mt-4 w-full rounded-xl border border-white/15 bg-black/55 px-3 py-2.5 font-mono text-sm"
            />
            <input
              placeholder="optional note"
              value={newLabel}
              disabled={busy}
              onChange={(e) => setNewLabel(e.target.value)}
              className="mt-3 w-full rounded-xl border border-white/15 bg-black/55 px-3 py-2.5 text-sm"
            />
            <div className="mt-6 flex justify-end gap-3">
              <button type="button" className="text-sm text-zinc-400" onClick={() => setCreateOpen(false)}>
                Cancel
              </button>
              <button type="button" disabled={busy} onClick={() => void createScriptKey()} className="rounded-xl bg-pollen px-4 py-2 text-sm font-bold text-black">
                Mint
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {minted ? (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 p-4" role="dialog" aria-modal>
          <div className="w-full max-w-lg rounded-3xl border border-pollen/35 bg-[#0a0a12] p-6">
            <h3 className="text-lg font-semibold text-pollen">Save this token once</h3>
            <pre className="mt-4 max-h-40 overflow-auto break-all rounded-xl border border-white/10 bg-black/55 p-3 font-mono text-xs">{minted.plaintext}</pre>
            <div className="mt-6 flex gap-3">
              <button type="button" className="rounded-xl border border-cyan px-4 py-2 text-sm text-cyan" onClick={() => copyPlaintext()}>
                Copy
              </button>
              <button type="button" className="rounded-xl bg-pollen px-4 py-2 text-sm font-bold text-black" onClick={() => setMinted(null)}>
                Stored safely
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
