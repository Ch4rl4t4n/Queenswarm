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
    <div className="flex flex-col gap-[var(--qs-gap)]">
      {err ? (
        <p className="qs-settings-card border-[var(--qs-red)]/30 bg-[var(--qs-red)]/10 py-3 text-sm text-[var(--qs-red)]">{err}</p>
      ) : null}

      <section className="qs-settings-card mb-0">
        <div className="qs-settings-card__header !items-start">
          <div className="min-w-0">
            <div className="qs-settings-card__title">External data APIs</div>
            <div className="qs-settings-card__subtitle">
              Encrypt JSON credential bundles per provider (Alpaca, Twitter/X, Yahoo, …). Keys never round-trip plaintext after save.
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-[var(--qs-gap)] sm:grid-cols-2 xl:grid-cols-3">
          {providers.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setSelectedProvider(p.id)}
              className={`w-full rounded-[var(--qs-radius)] border px-4 py-4 text-left transition ${
                selectedProvider === p.id ? "border-[var(--qs-amber)] bg-[color:rgb(255_184_0/0.08)]" : "border-[var(--qs-border)] bg-[var(--qs-bg)] hover:border-[var(--qs-cyan)]/35"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--qs-radius-sm)] border border-[var(--qs-border)] bg-[var(--qs-surface-2)] font-mono text-xs font-bold text-[var(--qs-amber)]">
                  {providerGlyph(p.id)}
                </div>
                <div className="min-w-0">
                  <p className="truncate font-semibold text-[var(--qs-text)]">{p.label}</p>
                  <p className="truncate font-mono text-[10px] uppercase text-[var(--qs-text-3)]">{p.id}</p>
                </div>
              </div>
              {selectedProvider === p.id ? <span className="qs-badge qs-badge--amber mt-3 inline-block font-mono">selected</span> : null}
            </button>
          ))}
        </div>

        <div className="mt-6 rounded-[var(--qs-radius-sm)] border border-[var(--qs-border)] bg-[var(--qs-bg)] p-4">
          <label htmlFor="ext-cred-label" className="qs-label">
            Label for this credential
          </label>
          <input
            id="ext-cred-label"
            value={credLabel}
            disabled={busy}
            onChange={(e) => setCredLabel(e.target.value)}
            className="qs-input"
            placeholder={`${selectedProvider.toUpperCase()} trading desk`}
          />
          <label htmlFor="ext-cred-json" className="qs-label mt-4">
            Credentials JSON (`key_id`, `secret`, `bearer_token`, …)
          </label>
          <textarea
            id="ext-cred-json"
            value={credJson}
            disabled={busy}
            onChange={(e) => setCredJson(e.target.value)}
            rows={5}
            className="qs-input min-h-[120px] resize-y text-xs"
          />
          <button type="button" disabled={busy} onClick={() => void addExternalCred()} className="qs-btn qs-btn--primary qs-btn--sm mt-4">
            Add encrypted key
          </button>
        </div>

        <div className="mt-8 space-y-3">
          <h3 className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-[var(--qs-text)]">Stored bundles</h3>
          {apis.length === 0 ? (
            <p className="text-sm text-[var(--qs-text-3)]">Nothing persisted yet.</p>
          ) : (
            apis.map((row) => (
              <div
                key={row.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--qs-radius-sm)] border border-[var(--qs-border)] bg-[var(--qs-bg)] px-4 py-3"
              >
                <div>
                  <p className="font-semibold text-[var(--qs-text)]">{row.label}</p>
                  <p className="font-mono text-xs text-[var(--qs-cyan)]">{row.provider}</p>
                  <pre className="mt-2 max-h-24 overflow-auto text-[10px] text-[var(--qs-text-3)]">{JSON.stringify(row.credentials_masked, null, 2)}</pre>
                </div>
                <button type="button" disabled={busy} onClick={() => void removeExternal(row.id)} className="qs-btn qs-btn--danger qs-btn--sm shrink-0">
                  Remove
                </button>
              </div>
            ))
          )}
        </div>
      </section>

      <section className="qs-settings-card mb-0">
        <div className="qs-settings-card__header !items-start">
          <div className="min-w-0">
            <div className="qs-settings-card__title">Hive script bearer keys</div>
            <div className="qs-settings-card__subtitle">
              Mint dashboard-scoped bearer tokens for automation ({MAX_SCRIPT_KEYS} concurrent slots).
            </div>
          </div>
        </div>

        {!rows ? (
          <div className="mt-2 h-32 animate-pulse rounded-[var(--qs-radius-sm)] bg-[var(--qs-surface-3)]/40" />
        ) : (
          <ul className="divide-y divide-[var(--qs-border)] border-t border-[var(--qs-border)]">
            {rows.map((row) => (
              <li key={row.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-mono text-sm text-[var(--qs-cyan)]">{row.source_name}</p>
                  <p className="text-xs text-[var(--qs-text-3)]">{row.masked_prefix}</p>
                </div>
                <button type="button" disabled={busy} onClick={() => void revokeScriptKey(row.id)} className="qs-btn qs-btn--danger qs-btn--sm shrink-0">
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
          className="qs-btn qs-btn--primary mt-6"
        >
          Mint script key
        </button>
      </section>

      {createOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4" role="dialog" aria-modal>
          <div className="qs-settings-card mb-0 w-full max-w-md border-[var(--qs-border)] bg-[var(--qs-surface)] p-[var(--qs-pad)] shadow-lg">
            <h3 className="qs-settings-card__title mb-4">New script slug</h3>
            <input
              placeholder="slug e.g. ci_main"
              value={newSourceName}
              disabled={busy}
              onChange={(e) => setNewSourceName(e.target.value)}
              className="qs-input font-mono text-sm"
            />
            <input
              placeholder="optional note"
              value={newLabel}
              disabled={busy}
              onChange={(e) => setNewLabel(e.target.value)}
              className="qs-input mt-3 text-sm"
            />
            <div className="mt-6 flex justify-end gap-3">
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm text-[var(--qs-text-2)]" onClick={() => setCreateOpen(false)}>
                Cancel
              </button>
              <button type="button" disabled={busy} onClick={() => void createScriptKey()} className="qs-btn qs-btn--primary qs-btn--sm">
                Mint
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {minted ? (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 p-4" role="dialog" aria-modal>
          <div className="qs-settings-card mb-0 w-full max-w-lg border-[var(--qs-amber)]/35 bg-[var(--qs-surface)] p-[var(--qs-pad)] shadow-lg">
            <h3 className="qs-settings-card__title text-[var(--qs-amber)]">Save this token once</h3>
            <pre className="mt-4 max-h-40 overflow-auto break-all rounded-[var(--qs-radius-sm)] border border-[var(--qs-border)] bg-[var(--qs-bg)] p-3 font-mono text-xs text-[var(--qs-text)]">
              {minted.plaintext}
            </pre>
            <div className="mt-6 flex gap-3">
              <button type="button" className="qs-btn qs-btn--cyan qs-btn--sm px-4" onClick={() => copyPlaintext()}>
                Copy
              </button>
              <button type="button" className="qs-btn qs-btn--primary qs-btn--sm px-4" onClick={() => setMinted(null)}>
                Stored safely
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
