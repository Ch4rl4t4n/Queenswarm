"use client";

import { X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { ConfirmModal } from "@/components/ui/ConfirmModal";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveDelete, hiveGet, hivePostJson } from "@/lib/api";
import type { ApiKeyCreated, ApiKeyListItem } from "@/lib/hive-dashboard-session";
import type { ExternalApiStoredRow, ExternalProviderMeta } from "@/lib/hive-types";
import { localizePhrase } from "@/lib/ui-copy";
import { cn } from "@/lib/utils";

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
  const { language } = useUiLanguage();
  const [providers, setProviders] = useState<ExternalProviderMeta[]>([]);
  const [apis, setApis] = useState<ExternalApiStoredRow[]>([]);
  const [rows, setRows] = useState<ApiKeyListItem[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ExternalApiStoredRow | null>(null);

  const [selectedProvider, setSelectedProvider] = useState<string>("alpaca");
  const [credLabel, setCredLabel] = useState("");
  const [credJson, setCredJson] = useState("{}");

  const [createOpen, setCreateOpen] = useState(false);
  const [newSourceName, setNewSourceName] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [minted, setMinted] = useState<ApiKeyCreated | null>(null);

  const apisByProvider = useMemo(() => {
    const map = new Map<string, ExternalApiStoredRow[]>();
    for (const row of apis) {
      const bucket = map.get(row.provider) ?? [];
      bucket.push(row);
      map.set(row.provider, bucket);
    }
    return map;
  }, [apis]);

  const loadExternal = useCallback(async () => {
    const [catalog, stash] = await Promise.all([
      hiveGet<{ providers: ExternalProviderMeta[] }>("external-apis/providers"),
      hiveGet<{ apis: ExternalApiStoredRow[] }>("external-apis/"),
    ]);
    setProviders(catalog.providers ?? []);
    setApis(stash.apis ?? []);
    setSelectedProvider((prev) => {
      if ((catalog.providers ?? []).some((p) => p.id === prev)) {
        return prev;
      }
      return catalog.providers[0]?.id ?? "alpaca";
    });
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
      toast.success(localizePhrase(language, { en: "Credential removed.", sk: "Poverenie odstránené." }));
      await loadExternal();
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Delete failed";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function confirmDeleteExternal(): Promise<void> {
    if (!deleteTarget) {
      return;
    }
    const id = deleteTarget.id;
    setDeleteTarget(null);
    await removeExternal(id);
  }

  function requestDeleteExternal(row: ExternalApiStoredRow): void {
    setDeleteTarget(row);
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
    <div className="flex flex-col gap-6">
      {err ? (
        <p className="rounded-xl border border-danger/30 bg-danger/6 px-4 py-3 text-sm text-danger" role="alert">
          {err}
        </p>
      ) : null}

      <V4Card>
        <V4CardHeader
          title="External data APIs"
          description="Encrypt JSON credential bundles per provider (Alpaca, Twitter/X, Yahoo, …). Keys never round-trip plaintext after save."
        />

        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {providers.map((p) => {
            const active = selectedProvider === p.id;
            const stored = apisByProvider.get(p.id) ?? [];
            const primaryStored = stored[0] ?? null;
            return (
              <div key={p.id} className="relative">
                {primaryStored ? (
                  <button
                    type="button"
                    disabled={busy}
                    aria-label={localizePhrase(language, {
                      en: `Delete stored API key for ${p.label}`,
                      sk: `Odstrániť uložený API kľúč pre ${p.label}`,
                    })}
                    className="absolute right-2 top-2 z-10 flex h-9 w-9 items-center justify-center rounded-lg border border-danger/45 bg-danger/12 text-danger transition hover:border-danger hover:bg-danger/20 touch-manipulation"
                    onClick={(event) => {
                      event.stopPropagation();
                      requestDeleteExternal(primaryStored);
                    }}
                  >
                    <X className="h-4 w-4" aria-hidden strokeWidth={2.5} />
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={() => setSelectedProvider(p.id)}
                  className={cn(
                    "v4-dream-cycle-card v4-card-interactive w-full text-left",
                    active && "border-pollen/45 bg-pollen/6 shadow-[0_0_24px_rgba(255,184,0,0.12)]",
                    primaryStored && "pt-8",
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-(--qs-border) bg-(--qs-surface-2) font-mono text-xs font-bold text-pollen">
                      {providerGlyph(p.id)}
                    </div>
                    <div className="min-w-0 pr-8">
                      <p className="truncate font-semibold text-(--qs-text)">{p.label}</p>
                      <p className="truncate font-mono text-[10px] uppercase text-(--qs-text-3)">{p.id}</p>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    {active ? (
                      <V4Badge tone="gold">selected</V4Badge>
                    ) : null}
                    {primaryStored ? (
                      <V4Badge tone="ok">
                        {localizePhrase(language, {
                          en: stored.length > 1 ? `${stored.length} keys saved` : "key saved",
                          sk: stored.length > 1 ? `${stored.length} kľúčov uložených` : "kľúč uložený",
                        })}
                      </V4Badge>
                    ) : null}
                  </div>
                </button>
              </div>
            );
          })}
        </div>

        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm mt-4 w-full sm:w-auto"
          onClick={() => document.getElementById("ext-cred-form")?.scrollIntoView({ behavior: "smooth", block: "start" })}
        >
          + New API connector
        </button>

        <div id="ext-cred-form" className="mt-4 rounded-xl border border-(--qs-border) bg-[rgba(7,3,15,0.35)] p-4">
          <label htmlFor="ext-cred-label" className="v4-field-label">
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
          <label htmlFor="ext-cred-json" className="v4-field-label mt-4">
            Credentials JSON (`key_id`, `secret`, `bearer_token`, …)
          </label>
          <textarea
            id="ext-cred-json"
            value={credJson}
            disabled={busy}
            onChange={(e) => setCredJson(e.target.value)}
            rows={5}
            className="qs-input min-h-[120px] resize-y font-mono text-xs"
          />
          <button type="button" disabled={busy} onClick={() => void addExternalCred()} className="qs-btn qs-btn--primary qs-btn--sm mt-4">
            Save key
          </button>
        </div>

        <div className="mt-4 border-t border-(--qs-border)/60 pt-4">
          <p className="v4-field-label mb-3">Stored bundles</p>
          {apis.length === 0 ? (
            <p className="text-sm text-(--qs-text-3)">Nothing persisted yet.</p>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {apis.map((row) => (
                <div
                  key={row.id}
                  className="relative rounded-xl border border-(--qs-border) bg-[rgba(7,3,15,0.35)] px-4 py-3 pt-10"
                >
                  <button
                    type="button"
                    disabled={busy}
                    aria-label={localizePhrase(language, {
                      en: `Delete API key ${row.label}`,
                      sk: `Odstrániť API kľúč ${row.label}`,
                    })}
                    className="absolute right-2 top-2 flex h-9 w-9 items-center justify-center rounded-lg border border-danger/45 bg-danger/12 text-danger transition hover:border-danger hover:bg-danger/20 touch-manipulation"
                    onClick={() => requestDeleteExternal(row)}
                  >
                    <X className="h-4 w-4" aria-hidden strokeWidth={2.5} />
                  </button>
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-(--qs-text)">{row.label}</p>
                    <p className="font-mono text-xs text-pollen">{row.provider}</p>
                    <pre className="mt-2 max-h-24 overflow-auto text-[10px] text-(--qs-text-3)">{JSON.stringify(row.credentials_masked, null, 2)}</pre>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </V4Card>

      <V4Card>
        <V4CardHeader
          title="Hive script bearer keys"
          description={`Mint dashboard-scoped bearer tokens for automation (${MAX_SCRIPT_KEYS} concurrent slots).`}
        />

        {!rows ? (
          <div className="mt-4 h-32 animate-pulse rounded-xl bg-white/4" />
        ) : rows.length === 0 ? (
          <p className="mt-4 text-sm text-(--qs-text-3)">No script keys minted yet.</p>
        ) : (
          <ul className="mt-4 divide-y divide-(--qs-border)">
            {rows.map((row) => (
              <li key={row.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-mono text-sm text-pollen">{row.source_name ?? row.label ?? row.id.slice(0, 8)}</p>
                  <p className="text-xs text-(--qs-text-3)">{row.masked_prefix}</p>
                  {row.revoked_at ? <V4Badge tone="err">revoked</V4Badge> : <V4Badge tone="ok">active</V4Badge>}
                </div>
                <button type="button" disabled={busy} onClick={() => void revokeScriptKey(row.id)} className="qs-btn qs-btn--ghost qs-btn--sm shrink-0 text-danger">
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
          className="qs-btn qs-btn--primary qs-btn--sm mt-6"
        >
          Mint script key
        </button>
      </V4Card>

      {createOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4" role="dialog" aria-modal>
          <div className="w-full max-w-md rounded-xl border border-(--qs-border) bg-(--qs-surface-2) p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-(--qs-text)">New script slug</h3>
            <input placeholder="slug e.g. ci_main" value={newSourceName} disabled={busy} onChange={(e) => setNewSourceName(e.target.value)} className="qs-input mt-4 font-mono text-sm" />
            <input placeholder="optional note" value={newLabel} disabled={busy} onChange={(e) => setNewLabel(e.target.value)} className="qs-input mt-3 text-sm" />
            <div className="mt-6 flex justify-end gap-3">
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => setCreateOpen(false)}>
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
          <div className="w-full max-w-lg rounded-xl border border-pollen/35 bg-(--qs-surface-2) p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-pollen">Save this token once</h3>
            <pre className="mt-4 max-h-40 overflow-auto break-all rounded-lg border border-(--qs-border) bg-[rgba(7,3,15,0.5)] p-3 font-mono text-xs text-(--qs-text)">
              {minted.plaintext}
            </pre>
            <div className="mt-6 flex gap-3">
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => copyPlaintext()}>
                Copy
              </button>
              <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" onClick={() => setMinted(null)}>
                Stored safely
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <ConfirmModal
        open={deleteTarget !== null}
        title={localizePhrase(language, {
          en: "Delete API key?",
          sk: "Odstrániť API kľúč?",
        })}
        message={
          deleteTarget
            ? localizePhrase(language, {
                en: `You are about to delete the configured API key “${deleteTarget.label}” (${deleteTarget.provider}). This cannot be undone. Are you sure?`,
                sk: `Chystáte sa odstrániť nastavený API kľúč „${deleteTarget.label}“ (${deleteTarget.provider}). Túto akciu nemožno vrátiť späť. Ste si istí?`,
              })
            : ""
        }
        confirmLabel={localizePhrase(language, { en: "Delete key", sk: "Odstrániť kľúč" })}
        danger
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => void confirmDeleteExternal()}
      />
    </div>
  );
}
