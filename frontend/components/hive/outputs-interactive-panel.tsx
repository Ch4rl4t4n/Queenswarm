"use client";

import { useCallback, useState } from "react";

import { V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveFetchRaw, hiveGet, hivePostJson } from "@/lib/api";
import type {
  FinalDeliverableDetailRow,
  FinalDeliverableSummaryRow,
  OutputsSearchResponse,
} from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface OutputsInteractivePanelProps {
  /** Server-rendered list — reset target when clearing search. */
  initialItems: FinalDeliverableSummaryRow[];
}

function summarizeFromDetail(row: FinalDeliverableDetailRow): FinalDeliverableSummaryRow {
  return {
    id: row.id,
    lineage_id: row.lineage_id,
    version: row.version,
    title: row.title,
    slug: row.slug,
    created_at: row.created_at,
    tags: row.tags,
    preview: row.preview,
  };
}

/** Client actions for Deliverables cockpit — semantic search + expand + regenerate + Markdown download. */
export function OutputsInteractivePanel({ initialItems }: OutputsInteractivePanelProps) {
  const [items, setItems] = useState<FinalDeliverableSummaryRow[]>(initialItems);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "ready">("all");
  const [searchBusy, setSearchBusy] = useState(false);
  const [filterBusy, setFilterBusy] = useState(false);
  const [regenBusyLineage, setRegenBusyLineage] = useState<string | null>(null);
  const [instruction, setInstruction] =
    useState("Tighten the executive summary and add clearer next-steps with owners.");
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detailById, setDetailById] = useState<Record<string, FinalDeliverableDetailRow>>({});

  const loadDetail = useCallback(async (id: string) => {
    setError(null);
    try {
      const row = await hiveGet<FinalDeliverableDetailRow>(`outputs/${encodeURIComponent(id)}`);
      setDetailById((prev) => (prev[id] ? prev : { ...prev, [id]: row }));
    } catch (e) {
      setError(e instanceof HiveApiError ? e.message : "Could not load full deliverable.");
    }
  }, []);

  async function onSearch(ev: React.FormEvent): Promise<void> {
    ev.preventDefault();
    const q = query.trim();
    setError(null);
    if (q.length < 2) {
      setItems(initialItems);
      return;
    }
    setSearchBusy(true);
    try {
      const res = await hiveGet<OutputsSearchResponse>(
        `outputs/search?q=${encodeURIComponent(q)}&limit=24`,
      );
      setItems(res.items);
    } catch (e) {
      setError(e instanceof HiveApiError ? e.message : "Semantic search failed.");
    } finally {
      setSearchBusy(false);
    }
  }

  function onClearSearch(): void {
    setQuery("");
    setItems(initialItems);
    setError(null);
  }

  async function onFilterReady(): Promise<void> {
    setFilterBusy(true);
    setError(null);
    setFilter("ready");
    try {
      const rows = await hiveGet<FinalDeliverableSummaryRow[]>("outputs?ready_to_publish=true&limit=40");
      setItems(rows);
    } catch (e) {
      setError(e instanceof HiveApiError ? e.message : "Ready-to-publish filter failed.");
    } finally {
      setFilterBusy(false);
    }
  }

  function onFilterAll(): void {
    setFilter("all");
    setItems(initialItems);
    setError(null);
  }

  async function onRegenerate(lineageId: string): Promise<void> {
    setRegenBusyLineage(lineageId);
    setError(null);
    try {
      const created = await hivePostJson<FinalDeliverableDetailRow>(
        `outputs/by-lineage/${encodeURIComponent(lineageId)}/regenerate`,
        { instruction: instruction.trim() },
      );
      const summary = summarizeFromDetail(created);
      setItems((prev) => [summary, ...prev.filter((r) => r.id !== summary.id)]);
      setDetailById((prev) => ({ ...prev, [summary.id]: created }));
      setExpandedId(summary.id);
    } catch (e) {
      setError(e instanceof HiveApiError ? e.message : "Regenerate failed (LLM keys required).");
    } finally {
      setRegenBusyLineage(null);
    }
  }

  async function onDownloadMarkdown(id: string, slug: string, version: number): Promise<void> {
    setError(null);
    try {
      const res = await hiveFetchRaw(`outputs/${encodeURIComponent(id)}/markdown.md`);
      if (!res.ok) {
        throw new HiveApiError(`Download HTTP ${res.status}`, res.status, await res.text());
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const safe = slug.replace(/\s+/g, "_").slice(0, 80) || "deliverable";
      const a = document.createElement("a");
      a.href = url;
      a.download = `${safe}_v${version}.md`;
      a.rel = "noopener";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof HiveApiError ? e.message : "Markdown download failed.");
    }
  }

  async function toggleExpand(id: string): Promise<void> {
    if (expandedId === id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(id);
    await loadDetail(id);
  }

  return (
    <div className="flex flex-col gap-6">
      <V4Card>
        <V4CardHeader
          title="Publish queue (Phase A)"
          description="Verified publish packs — simulate_only, critic-approved. Live Instagram is Phase C."
        />
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className={cn("qs-btn qs-btn--sm", filter === "all" ? "qs-btn--primary" : "qs-btn--ghost")}
            onClick={() => onFilterAll()}
          >
            All outputs
          </button>
          <button
            type="button"
            className={cn("qs-btn qs-btn--sm", filter === "ready" ? "qs-btn--primary" : "qs-btn--ghost")}
            disabled={filterBusy}
            onClick={() => void onFilterReady()}
          >
            {filterBusy ? "Loading…" : "Ready to publish"}
          </button>
        </div>
      </V4Card>

      <V4Card>
        <V4CardHeader
          title="Semantic search"
          description="Embedding index mirrors titled Markdown; scope is rows you own on this dashboard JWT."
        />
        <form onSubmit={(e) => void onSearch(e)} className="flex flex-col gap-3 lg:flex-row lg:items-end">
          <div className="flex-1 space-y-1.5">
            <label htmlFor="outputs-search-q" className="sr-only">
              Semantic search across archived deliverables
            </label>
            <input
              id="outputs-search-q"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Semantic search (Chroma) — min 2 characters…"
              className="qs-input w-full"
            />
          </div>
          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
            <button type="submit" className="qs-btn qs-btn--primary qs-btn--sm w-full sm:w-auto" disabled={searchBusy}>
              {searchBusy ? "Searching…" : "Search"}
            </button>
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm w-full sm:w-auto" onClick={() => onClearSearch()}>
              Reset list
            </button>
          </div>
        </form>
      </V4Card>

      <V4Card>
        <V4CardHeader
          title="Regenerate (LiteLLM)"
          description="Picks latest version per lineage — produces v+1 with merged structured JSON when the orch returns SECTION_JSON."
        />
        <textarea
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          rows={3}
          className="v4-textarea font-mono text-xs leading-relaxed"
          spellCheck={false}
        />
      </V4Card>

      {error ? <p className="text-sm text-(--qs-red)">{error}</p> : null}

      <ul className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {items.map((row) => {
          const open = expandedId === row.id;
          const detail = detailById[row.id];
          return (
            <li key={row.id}>
              <article className={cn("v4-dream-cycle-card flex flex-col gap-3", open && "border-(--qs-amber)/35")}>
                <header className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="v4-label-kicker">Lineage · v{row.version}</p>
                    <h3 className="text-lg font-semibold text-(--qs-text)">{row.title}</h3>
                  </div>
                  <span className="shrink-0 rounded-full border border-(--qs-border) px-2 py-1 font-mono text-[11px] text-(--qs-text-3)">
                    {new Date(row.created_at).toLocaleString()}
                  </span>
                </header>
                {(row.tags ?? []).length ? (
                  <div className="flex flex-wrap gap-2">
                    {row.tags.slice(0, 8).map((t) => (
                      <span key={t} className="rounded-full bg-white/4 px-2 py-0.5 text-[10px] text-(--qs-amber)">
                        #{t}
                      </span>
                    ))}
                  </div>
                ) : null}
                <p className="text-sm leading-relaxed text-(--qs-text-2)">{row.preview}</p>
                <div className="v4-dream-cycle-card-actions">
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    onClick={() => void onDownloadMarkdown(row.id, row.slug, row.version)}
                  >
                    Download MD
                  </button>
                  <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" disabled title="PDF export returns 501 by design">
                    PDF
                  </button>
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm text-(--qs-amber)"
                    disabled={regenBusyLineage === row.lineage_id || instruction.trim().length < 4}
                    onClick={() => void onRegenerate(row.lineage_id)}
                  >
                    {regenBusyLineage === row.lineage_id ? "Regenerating…" : "Regenerate"}
                  </button>
                  <button
                    type="button"
                    className={cn("qs-btn qs-btn--sm", open ? "qs-btn--ghost" : "qs-btn--primary")}
                    onClick={() => void toggleExpand(row.id)}
                  >
                    {open ? "Collapse" : "View full"}
                  </button>
                </div>
                {open && detail ? (
                  <div className="space-y-3 border-t border-(--qs-border) pt-4">
                    <pre className="hive-scrollbar max-h-[min(52vh,480px)] overflow-auto whitespace-pre-wrap rounded-(--qs-radius-sm) border border-(--qs-border) bg-black/40 p-3 font-mono text-[12px] text-(--qs-text-2)">
                      {detail.markdown_body}
                    </pre>
                    {detail.voice_script ? (
                      <div>
                        <p className="v4-label-kicker mb-1">SECTION_VOICE (preview)</p>
                        <p className="rounded-(--qs-radius-sm) border border-(--qs-border) bg-white/2 p-3 text-sm text-(--qs-text-2)">
                          {detail.voice_script.slice(0, 1200)}
                          {detail.voice_script.length > 1200 ? "…" : ""}
                        </p>
                      </div>
                    ) : null}
                    <details className="rounded-(--qs-radius-sm) border border-(--qs-border) bg-white/2 p-3">
                      <summary className="cursor-pointer text-xs font-semibold text-(--qs-text-2)">
                        Structured JSON
                      </summary>
                      <pre className="mt-2 max-h-48 overflow-auto font-mono text-[11px] text-(--qs-text-3)">
                        {JSON.stringify(detail.structured_json, null, 2)}
                      </pre>
                    </details>
                  </div>
                ) : null}
              </article>
            </li>
          );
        })}
      </ul>

      {items.length === 0 ? (
        <p className="v4-dream-empty">
          Nothing here yet — finish a Ballroom mission while logged into the cockpit to attach artefacts to your account.
        </p>
      ) : null}
    </div>
  );
}
