"use client";

import { useCallback, useEffect, useState } from "react";

import { QsSelect } from "@/components/ui/qs-select";
import { V4Card, V4CardHeader } from "@/components/ui/v4";
import type { PublicShareRow } from "@/lib/hive-types";

const RESOURCE_TYPES = ["output", "session", "swarm"] as const;
const RESOURCE_TYPE_OPTIONS = RESOURCE_TYPES.map((row) => ({ value: row, label: row }));

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
    <div className="flex flex-col gap-6">
      <V4Card>
        <V4CardHeader
          title="Public sharing"
          description="Generate read-only public links for outputs, supervisor sessions, and swarms."
        />
      </V4Card>

      <V4Card>
        <V4CardHeader title="Create link" description="Resource type, UUID, and expiry in days." />
        <div className="v4-settings-sharing-form grid gap-3 md:grid-cols-[auto_1fr_auto_auto]">
          <QsSelect
            value={resourceType}
            onValueChange={(next) => setResourceType(next as (typeof RESOURCE_TYPES)[number])}
            className="min-h-11 rounded-(--qs-radius-sm) text-sm"
            disabled={busy}
            options={RESOURCE_TYPE_OPTIONS}
          />
          <input
            value={resourceId}
            onChange={(event) => setResourceId(event.target.value)}
            placeholder="Resource UUID"
            className="qs-input"
            disabled={busy}
          />
          <input
            value={expiresInDays}
            onChange={(event) => setExpiresInDays(event.target.value)}
            placeholder="Expires (days)"
            className="qs-input"
            disabled={busy}
          />
          <button
            type="button"
            onClick={() => void createShare()}
            disabled={busy || !resourceId.trim()}
            className="qs-btn qs-btn--primary qs-btn--sm"
          >
            Create
          </button>
        </div>
      </V4Card>

      <V4Card>
        <V4CardHeader title="Active links" description="Read-only public URLs scoped to your tenant." />
        {loading ? (
          <p className="text-sm text-(--qs-text-3)">Loading links…</p>
        ) : rows.length === 0 ? (
          <p className="text-sm text-(--qs-text-3)">No share links yet.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {rows.map((row) => (
              <article
                key={row.id}
                className="rounded-(--qs-radius-sm) border border-(--qs-border) bg-white/2 p-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm text-(--qs-text)">
                    {row.resource_type} · {row.resource_id}
                  </p>
                  <button
                    type="button"
                    onClick={() => void revokeShare(row.id)}
                    disabled={busy || !row.is_active}
                    className="qs-btn qs-btn--danger qs-btn--sm"
                  >
                    Revoke
                  </button>
                </div>
                <p className="mt-1 break-all font-mono text-xs text-(--qs-text-2)">{row.public_url}</p>
                <p className="mt-1 text-xs text-(--qs-text-3)">
                  views {row.access_count} · expires {row.expires_at ? new Date(row.expires_at).toLocaleString() : "never"}
                </p>
              </article>
            ))}
          </div>
        )}
      </V4Card>

      {error ? <p className="text-sm text-(--qs-red)">{error}</p> : null}
    </div>
  );
}
