"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { NeonButton } from "@/components/ui/neon-button";
import { HiveApiError, hiveDelete, hiveGet, hivePostJson } from "@/lib/api";
import type { ApiKeyCreated, ApiKeyListItem } from "@/lib/hive-dashboard-session";

export default function SettingsApiKeysPage() {
  const [rows, setRows] = useState<ApiKeyListItem[]>([]);
  const [freshPlaintext, setFreshPlaintext] = useState<string | null>(null);
  const [label, setLabel] = useState("");

  const reload = useCallback(async () => {
    try {
      const list = await hiveGet<ApiKeyListItem[]>("auth/api-keys");
      setRows(list ?? []);
    } catch {
      setRows([]);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function mintKey(): Promise<void> {
    try {
      const out = await hivePostJson<ApiKeyCreated>("auth/api-keys", { label: label.trim() || null });
      setFreshPlaintext(out.plaintext);
      setLabel("");
      toast.success("Key minted once — ulož ju mimo dashboard.");
      await reload();
    } catch (e) {
      if (e instanceof HiveApiError) toast.error(e.message);
      else toast.error("Mint failed.");
    }
  }

  async function revokeKey(id: string): Promise<void> {
    try {
      await hiveDelete(`auth/api-keys/${id}`);
      toast.success("Key revoked.");
      await reload();
    } catch (e) {
      if (e instanceof HiveApiError) toast.error(e.message);
      else toast.error("Revoke failed.");
    }
  }

  function formatMeta(row: ApiKeyListItem): string {
    const created = new Date(row.created_at).toISOString().slice(0, 10);
    if (row.revoked_at) return `Created ${created} · revoked`;
    return `Created ${created} · Bearer \`dash:user:*\``;
  }

  return (
    <article className="rounded-2xl border border-cyan/[0.12] bg-hive-card/90 p-6 md:p-8">
      <h2 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">API keys</h2>
      <p className="mt-2 font-[family-name:var(--font-inter)] text-sm text-muted-foreground">
        Bearer prefix {"qs_kw_"} tokeny nahradajú session JWT pre skripty · rotuj priebežne · nikdy do LLM.
      </p>
      {freshPlaintext ? (
        <div className="mt-6 rounded-xl border border-pollen/30 bg-black/40 p-4">
          <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs uppercase tracking-[0.15em] text-pollen">
            New key (kopíruj teraz)
          </p>
          <code className="mt-2 block break-all font-mono text-sm text-[#fafafa]">{freshPlaintext}</code>
          <NeonButton type="button" variant="ghost" className="mt-3 text-xs" onClick={() => setFreshPlaintext(null)}>
            Skryť
          </NeonButton>
        </div>
      ) : null}

      <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="flex-1 space-y-1">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.2em] text-zinc-500">
            Označenie (voliteľné)
          </span>
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            className="w-full rounded-xl border border-cyan/[0.15] bg-black/45 px-4 py-2 text-sm text-[#fafafa]"
          />
        </label>
        <NeonButton type="button" variant="primary" className="sm:shrink-0" onClick={() => void mintKey()}>
          + New key
        </NeonButton>
      </div>

      <ul className="mt-8 divide-y divide-cyan/[0.08]">
        {rows.map((row) => (
          <li key={row.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <code className="font-[family-name:var(--font-jetbrains-mono)] text-sm text-data">{row.masked_prefix}</code>
                {row.revoked_at ? (
                  <span className="rounded-full border border-zinc-600 px-2 py-0.5 font-mono text-[10px] text-zinc-500">
                    REVOKED
                  </span>
                ) : null}
              </div>
              <p className="mt-1 font-[family-name:var(--font-inter)] text-xs text-zinc-500">{formatMeta(row)}</p>
              {row.label ? (
                <p className="mt-1 font-[family-name:var(--font-inter)] text-xs text-muted-foreground">{row.label}</p>
              ) : null}
            </div>
            <NeonButton
              type="button"
              variant="ghost"
              className="shrink-0 text-danger disabled:opacity-40"
              disabled={!!row.revoked_at}
              onClick={() => void revokeKey(row.id)}
            >
              Revoke
            </NeonButton>
          </li>
        ))}
      </ul>

      {!rows.length ? (
        <p className="mt-6 font-[family-name:var(--font-inter)] text-sm text-zinc-500">Žiadne uložené kľúče.</p>
      ) : null}
    </article>
  );
}
