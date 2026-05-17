"use client";

import { useCallback, useEffect, useState } from "react";

import type { PublicShareRow } from "@/lib/hive-types";

const RESOURCE_TYPES = ["output", "session", "swarm"] as const;

export function SharingSettingsPanel() {
  const [rows, setRows] = useState<PublicShareRow[]>([]);
  const [resourceType, setResourceType] = useState<(typeof RESOURCE_TYPES)[number]>("output");
  const [resourceId, setResourceId] = useState("");
  const [expiresInDays, setExpiresInDays] = useState("30");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/proxy/shares", { cache: "no-store" });
      const json = (await res.json().catch(() => [])) as PublicShareRow[] | { detail?: string };
      if (!res.ok) {
        throw new Error(Array.isArray(json) ? "Load failed." : String(json.detail ?? "Load failed."));
      }
      setRows(Array.isArray(json) ? json : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load shares.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const createShare = useCallback(async () => {
    if (!resourceId.trim()) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const body = {
        resource_type: resourceType,
        resource_id: resourceId.trim(),
        expires_in_days: Math.max(1, Number(expiresInDays || "30")),
      };
      const res = await fetch("/api/proxy/shares", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(String((json as { detail?: string }).detail ?? "Create share failed"));
      }
      setResourceId("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create share failed.");
    } finally {
      setBusy(false);
    }
  }, [expiresInDays, load, resourceId, resourceType]);

  const revokeShare = useCallback(async (id: string) => {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/proxy/shares/${id}`, { method: "DELETE" });
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        throw new Error(String((json as { detail?: string }).detail ?? "Revoke failed"));
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Revoke failed.");
    } finally {
      setBusy(false);
    }
  }, [load]);

  return (
    <section className="space-y-6">
      <header className="rounded-2xl border border-cyan/15 bg-hive-card/70 p-5">
        <h2 className="text-lg font-semibold text-zinc-100">Public sharing</h2>
        <p className="mt-2 text-sm text-zinc-400">
          Generate read-only public links for outputs, supervisor sessions, and swarms.
        </p>
      </header>

      <div className="rounded-2xl border border-cyan/15 bg-hive-card/70 p-5">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-200">Create link</h3>
        <div className="mt-3 grid gap-3 md:grid-cols-[auto_1fr_auto_auto]">
          <select
            value={resourceType}
            onChange={(event) => setResourceType(event.target.value as (typeof RESOURCE_TYPES)[number])}
            className="rounded-xl border border-cyan/20 bg-hive-void/70 px-3 py-2 text-sm text-zinc-100"
            disabled={busy}
          >
            {RESOURCE_TYPES.map((row) => (
              <option key={row} value={row}>
                {row}
              </option>
            ))}
          </select>
          <input
            value={resourceId}
            onChange={(event) => setResourceId(event.target.value)}
            placeholder="Resource UUID"
            className="rounded-xl border border-cyan/20 bg-hive-void/70 px-3 py-2 text-sm text-zinc-100"
            disabled={busy}
          />
          <input
            value={expiresInDays}
            onChange={(event) => setExpiresInDays(event.target.value)}
            placeholder="Expires (days)"
            className="rounded-xl border border-cyan/20 bg-hive-void/70 px-3 py-2 text-sm text-zinc-100"
            disabled={busy}
          />
          <button
            type="button"
            onClick={() => void createShare()}
            disabled={busy || !resourceId.trim()}
            className="rounded-xl bg-amber-400 px-4 py-2 text-sm font-semibold text-black transition enabled:hover:bg-amber-300 disabled:opacity-50"
          >
            Create
          </button>
        </div>
      </div>

      <div className="rounded-2xl border border-cyan/15 bg-hive-card/70 p-5">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-200">Active links</h3>
        {loading ? (
          <p className="mt-3 text-sm text-zinc-500">Loading links…</p>
        ) : rows.length === 0 ? (
          <p className="mt-3 text-sm text-zinc-500">No share links yet.</p>
        ) : (
          <div className="mt-3 space-y-2">
            {rows.map((row) => (
              <article key={row.id} className="rounded-xl border border-cyan/10 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm text-zinc-100">
                    {row.resource_type} · {row.resource_id}
                  </p>
                  <button
                    type="button"
                    onClick={() => void revokeShare(row.id)}
                    disabled={busy || !row.is_active}
                    className="rounded-lg border border-rose-400/40 px-3 py-1 text-xs text-rose-200 enabled:hover:bg-rose-500/20 disabled:opacity-50"
                  >
                    Revoke
                  </button>
                </div>
                <p className="mt-1 break-all font-mono text-xs text-cyan-300">{row.public_url}</p>
                <p className="mt-1 text-xs text-zinc-500">
                  views {row.access_count} · expires {row.expires_at ? new Date(row.expires_at).toLocaleString() : "never"}
                </p>
              </article>
            ))}
          </div>
        )}
      </div>
      {error ? <p className="text-sm text-rose-300">{error}</p> : null}
    </section>
  );
}
