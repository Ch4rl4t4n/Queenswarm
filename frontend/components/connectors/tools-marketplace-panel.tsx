"use client";

import type { JSX } from "react";
import { useEffect, useMemo, useState } from "react";

import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

interface MarketplaceTemplateRow {
  source: string;
  id: string;
  slug: string;
  title: string;
  summary: string;
  category: string;
  auth_type: string;
  tool_count: number;
  installed: boolean;
}

interface MarketplaceCatalogResponse {
  phase3_templates: MarketplaceTemplateRow[];
}

export function ToolsMarketplacePanel(): JSX.Element {
  const [rows, setRows] = useState<MarketplaceTemplateRow[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [installedId, setInstalledId] = useState<string | null>(null);

  async function load(): Promise<void> {
    setError(null);
    try {
      const payload = await hiveGet<MarketplaceCatalogResponse>("tools/marketplace/catalog");
      setRows(payload.phase3_templates ?? []);
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Marketplace unavailable.";
      setError(detail);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const grouped = useMemo(() => {
    const box: Record<string, MarketplaceTemplateRow[]> = {};
    for (const row of rows) {
      const key = row.category || "other";
      if (!box[key]) {
        box[key] = [];
      }
      box[key]?.push(row);
    }
    return box;
  }, [rows]);

  async function install(row: MarketplaceTemplateRow): Promise<void> {
    setBusyId(row.id);
    setError(null);
    try {
      await hivePostJson("tools/marketplace/install", {
        source: row.source || "phase3_template",
        entry_id: row.id,
      });
      setInstalledId(row.id);
      await load();
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Install failed.";
      setError(detail);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="space-y-4 rounded-2xl border border-zinc-800 bg-black/25 p-4">
      <header className="space-y-1">
        <h3 className="text-sm font-semibold text-zinc-100 md:text-base">API Marketplace Foundation</h3>
        <p className="text-xs text-zinc-400 md:text-sm">
          One-click install for curated connector templates; custom/community sources can plug into the same install API.
        </p>
      </header>
      {error ? (
        <p className="rounded-xl border border-[#FF3366]/35 bg-[#FF3366]/10 px-3 py-2 text-xs text-[#FF3366]">{error}</p>
      ) : null}
      {Object.entries(grouped).map(([category, categoryRows]) => (
        <div key={category} className="space-y-2">
          <p className="text-[11px] uppercase tracking-widest text-cyan">{category.replaceAll("_", " ")}</p>
          <div className="grid gap-2 md:grid-cols-2">
            {categoryRows.map((row) => (
              <article key={row.id} className="rounded-xl border border-zinc-800 bg-black/30 p-3">
                <p className="text-sm font-semibold text-zinc-100">{row.title}</p>
                <p className="mt-1 text-xs text-zinc-400">{row.summary}</p>
                <p className="mt-1 text-[11px] text-zinc-500">
                  `{row.slug}` · {row.auth_type} · {row.tool_count} tools
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.08em] ${
                      row.installed ? "border-[#00FF88]/40 bg-[#00FF88]/10 text-[#00FF88]" : "border-zinc-700 text-zinc-400"
                    }`}
                  >
                    {row.installed ? "installed" : "not installed"}
                  </span>
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    disabled={row.installed || busyId === row.id}
                    onClick={() => void install(row)}
                  >
                    {busyId === row.id ? "Installing…" : "Install one-click"}
                  </button>
                </div>
                {installedId === row.id ? (
                  <p className="mt-1 text-[11px] text-[#00FF88]">Installed. Run “Test connection” in Dynamic Hub to activate.</p>
                ) : null}
              </article>
            ))}
          </div>
        </div>
      ))}
      {!rows.length && !error ? <p className="text-sm text-zinc-500">Loading marketplace catalog…</p> : null}
    </section>
  );
}
