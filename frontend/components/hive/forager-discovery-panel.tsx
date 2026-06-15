"use client";

import { Loader2, Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { ForagerRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface DiscoveryWizardSnapshot {
  enabled: boolean;
  keys_configured: boolean;
  tavily_configured: boolean;
  serper_configured: boolean;
  max_urls: number;
  operator_hint?: string;
}

interface DiscoveryUrlHit {
  url: string;
  title: string;
  snippet: string;
  provider: string;
  url_kind: string;
}

interface DiscoverySearchPayload {
  enabled: boolean;
  query: string;
  hits: DiscoveryUrlHit[];
  providers_used: string[];
  keys_configured: boolean;
  operator_hint?: string;
}

interface ForagerDiscoveryPanelProps {
  canManage: boolean;
  foragers: ForagerRow[];
  onBound: () => Promise<void>;
}

/** DG6 — Serper/Tavily URL discovery → bind forager. */
export function ForagerDiscoveryPanel({
  canManage,
  foragers,
  onBound,
}: ForagerDiscoveryPanelProps): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<DiscoveryWizardSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [hits, setHits] = useState<DiscoveryUrlHit[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [foragerId, setForagerId] = useState("");
  const [binding, setBinding] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<DiscoveryWizardSnapshot>("foragers/discovery-wizard");
      setSnapshot(data);
    } catch {
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const search = useCallback(async () => {
    const trimmed = query.trim();
    if (trimmed.length < 4) return;
    setSearching(true);
    try {
      const data = await hivePostJson<DiscoverySearchPayload>("foragers/discovery-wizard/search", {
        query: trimmed,
        limit: snapshot?.max_urls ?? 8,
      });
      setHits(data.hits);
      setSelected(new Set(data.hits.map((hit) => hit.url)));
    } catch (e) {
      setHits([]);
      toast.error(e instanceof HiveApiError ? e.message : "Discovery search failed");
    } finally {
      setSearching(false);
    }
  }, [query, snapshot?.max_urls]);

  const toggleUrl = (url: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(url)) {
        next.delete(url);
      } else {
        next.add(url);
      }
      return next;
    });
  };

  const bind = useCallback(async () => {
    const urls = hits.filter((hit) => selected.has(hit.url)).map((hit) => hit.url);
    if (!urls.length) {
      toast.error("Select at least one URL");
      return;
    }
    setBinding(true);
    try {
      const data = await hivePostJson<{
        ok: boolean;
        message: string;
        forager_name: string;
      }>("foragers/discovery-wizard/bind", {
        forager_id: foragerId || null,
        urls,
        intent: foragerId ? null : query.trim() || null,
        trigger_first_run: true,
      });
      toast.success(data.message || `${data.forager_name} updated`);
      setHits([]);
      setSelected(new Set());
      await onBound();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Bind failed");
    } finally {
      setBinding(false);
    }
  }, [foragerId, hits, onBound, query, selected]);

  if (loading && !snapshot) {
    return (
      <V4Card className="border-magenta/20 bg-magenta/5">
        <div className="flex items-center gap-2 p-4 text-sm text-(--qs-text-3)">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          Loading discovery wizard…
        </div>
      </V4Card>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  const foragerOptions = [
    { value: "", label: "Create new monitor" },
    ...foragers.map((row) => ({ value: row.id, label: row.name })),
  ];

  return (
    <div data-testid="forager-discovery-panel">
      <V4Card className="border-magenta/20 bg-magenta/5">
        <V4CardHeader
          title="Discovery-first scrape"
          description="DG6 — Serper/Tavily finds URLs; bind feeds or channels to a forager."
        />
        <div className="flex flex-col gap-3">
          {!snapshot.keys_configured ? (
            <p className="text-xs text-(--qs-text-3)">
              Add Tavily or Serper in Settings → Integrations → Research keys to discover URLs.
            </p>
          ) : null}
          <div className="flex flex-wrap items-end gap-2">
            <label className="flex min-w-[220px] flex-1 flex-col gap-1.5">
              <span className="text-xs font-medium text-(--qs-text-2)">Search query</span>
              <input
                className="qs-input"
                placeholder="e.g. EU python job board RSS feed"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={!canManage}
              />
            </label>
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm gap-2"
              disabled={!canManage || searching || query.trim().length < 4}
              onClick={() => void search()}
            >
              {searching ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Search className="h-4 w-4" aria-hidden />}
              Discover
            </button>
          </div>
          {hits.length > 0 ? (
            <ul className="space-y-2">
              {hits.map((hit) => (
                <li
                  key={hit.url}
                  className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs"
                >
                  <label className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      className="mt-0.5"
                      checked={selected.has(hit.url)}
                      onChange={() => toggleUrl(hit.url)}
                      disabled={!canManage}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="font-medium text-(--qs-text-1)">{hit.title}</span>
                      <div className="mt-1 flex flex-wrap gap-1.5">
                        <V4Badge tone="info">{hit.url_kind}</V4Badge>
                        <V4Badge tone="purple">{hit.provider}</V4Badge>
                      </div>
                      <p className="mt-1 truncate text-(--qs-text-3)">{hit.url}</p>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          ) : null}
          {hits.length > 0 ? (
            <div className="flex flex-wrap items-end gap-3">
              <label className="flex min-w-[200px] flex-col gap-1.5">
                <span className="text-xs font-medium text-(--qs-text-2)">Bind to</span>
                <QsSelect
                  value={foragerId}
                  onValueChange={setForagerId}
                  options={foragerOptions}
                  disabled={!canManage}
                />
              </label>
              <button
                type="button"
                className={cn("qs-btn qs-btn--primary qs-btn--sm")}
                disabled={!canManage || binding || selected.size === 0}
                onClick={() => void bind()}
              >
                {binding ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
                Bind {selected.size} URL{selected.size === 1 ? "" : "s"}
              </button>
            </div>
          ) : null}
        </div>
      </V4Card>
    </div>
  );
}
