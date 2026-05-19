"use client";

import type { JSX } from "react";
import { useEffect, useMemo, useState } from "react";

import { V4Badge, V4CardHeader } from "@/components/ui/v4";
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

function categoryLabel(category: string): string {
  return category.replaceAll("_", " ");
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
    <div className="space-y-6">
      <V4CardHeader
        as="h3"
        title="API marketplace foundation"
        description="One-click install for curated connector templates; custom and community sources plug into the same install API."
      />

      {error ? (
        <p className="rounded-xl border border-(--qs-red)/35 bg-(--qs-red)/10 px-3 py-2 text-xs text-(--qs-red)">{error}</p>
      ) : null}

      {Object.entries(grouped).map(([category, categoryRows]) => (
        <div key={category} className="space-y-3">
          <p className="v4-field-label">{categoryLabel(category)}</p>
          <div className="grid gap-3 md:grid-cols-2">
            {categoryRows.map((row) => (
              <article key={row.id} className="v4-dream-cycle-card flex flex-col gap-3">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-semibold text-(--qs-text)">{row.title}</p>
                  <V4Badge tone={row.installed ? "ok" : "warn"}>{row.installed ? "installed" : "not installed"}</V4Badge>
                </div>
                <p className="text-xs text-(--qs-text-3)">{row.summary}</p>
                <p className="font-mono text-[11px] text-(--qs-text-3)">
                  {row.slug} · {row.auth_type} · {row.tool_count} tools
                </p>
                <div className="mt-auto flex flex-wrap items-center gap-2">
                  {!row.installed ? (
                    <button
                      type="button"
                      className="qs-btn qs-btn--primary qs-btn--sm"
                      disabled={busyId === row.id}
                      onClick={() => void install(row)}
                    >
                      {busyId === row.id ? "Installing…" : "Install one-click"}
                    </button>
                  ) : (
                    <span className="text-[11px] text-(--qs-green)">Ready in connector hub — run test connection to activate.</span>
                  )}
                </div>
                {installedId === row.id ? (
                  <p className="text-[11px] text-(--qs-green)">Installed. Open Connector hub to test the connection.</p>
                ) : null}
              </article>
            ))}
          </div>
        </div>
      ))}

      {!rows.length && !error ? <p className="text-sm text-(--qs-text-3)">Loading marketplace catalog…</p> : null}
    </div>
  );
}
