"use client";

import { useCallback, useState } from "react";

import { NeonButton } from "@/components/ui/neon-button";
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
  const [searchBusy, setSearchBusy] = useState(false);
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
    <div className="space-y-6">
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
            className="w-full rounded-xl border border-cyan/[0.14] bg-hive-card/90 px-4 py-2.5 font-[family-name:var(--font-poppins)] text-sm text-[#fafafa] placeholder:text-zinc-500 focus:border-pollen/35 focus:outline-none"
          />
          <p className="font-[family-name:var(--font-poppins)] text-[11px] text-zinc-500">
            Embedding index mirrors titled Markdown; scope is rows you own on this dashboard JWT.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <NeonButton type="submit" variant="primary" disabled={searchBusy} className="uppercase tracking-[0.1em]">
            {searchBusy ? "Searching…" : "Search"}
          </NeonButton>
          <NeonButton type="button" variant="ghost" onClick={() => onClearSearch()} className="uppercase tracking-[0.1em]">
            Reset list
          </NeonButton>
        </div>
      </form>

      <section className="rounded-2xl border border-cyan/[0.1] bg-hive-card/40 p-4">
        <h2 className="font-[family-name:var(--font-poppins)] text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500">
          Regenerate (LiteLLM)
        </h2>
        <p className="mt-2 font-[family-name:var(--font-poppins)] text-xs text-muted-foreground">
          Picks latest version per lineage — produces v+1 with merged structured JSON when the orch returns SECTION_JSON.
        </p>
        <textarea
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          rows={3}
          className="mt-3 w-full rounded-xl border border-cyan/[0.12] bg-[#050510]/80 px-3 py-2 font-[family-name:var(--font-jetbrains)] text-[13px] text-data focus:border-pollen/30 focus:outline-none"
          spellCheck={false}
        />
      </section>

      {error ? (
        <p className="rounded-xl border border-danger/30 bg-danger/[0.08] px-4 py-2 font-[family-name:var(--font-poppins)] text-sm text-danger">
          {error}
        </p>
      ) : null}

      <ul className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {items.map((row) => {
          const open = expandedId === row.id;
          const detail = detailById[row.id];
          return (
            <li key={row.id}>
              <article
                className={cn(
                  "flex flex-col gap-3 rounded-[22px] border border-cyan/[0.09] bg-hive-card/95 p-5 shadow-[inset_0_0_0_1px_rgb(0_255_255/0.04)] transition hover:border-pollen/25",
                  open && "border-pollen/35 shadow-[inset_0_0_0_1px_rgb(255_184_0/0.12)]",
                )}
              >
                <header className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-[family-name:var(--font-poppins)] text-[10px] uppercase tracking-[0.15em] text-zinc-500">
                      Lineage · v{row.version}
                    </p>
                    <h3 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#fafafa]">{row.title}</h3>
                  </div>
                  <span className="shrink-0 rounded-full border border-data/35 px-2 py-1 font-[family-name:var(--font-jetbrains)] text-[11px] text-data">
                    {new Date(row.created_at).toLocaleString()}
                  </span>
                </header>
                {(row.tags ?? []).length ? (
                  <div className="flex flex-wrap gap-2">
                    {row.tags.slice(0, 8).map((t) => (
                      <span key={t} className="rounded-full bg-black/35 px-2 py-0.5 font-[family-name:var(--font-poppins)] text-[10px] text-pollen">
                        #{t}
                      </span>
                    ))}
                  </div>
                ) : null}
                <p className="font-[family-name:var(--font-poppins)] text-sm leading-relaxed text-zinc-300">{row.preview}</p>
                <div className="flex flex-wrap gap-2">
                  <NeonButton type="button" variant={open ? "primary" : "ghost"} onClick={() => void toggleExpand(row.id)}>
                    {open ? "Collapse" : "View full"}
                  </NeonButton>
                  <NeonButton type="button" variant="ghost" onClick={() => void onDownloadMarkdown(row.id, row.slug, row.version)}>
                    Download MD
                  </NeonButton>
                  <NeonButton type="button" variant="ghost" disabled title="PDF export returns 501 by design">
                    PDF
                  </NeonButton>
                  <NeonButton
                    type="button"
                    variant="ghost"
                    disabled={regenBusyLineage === row.lineage_id || instruction.trim().length < 4}
                    onClick={() => void onRegenerate(row.lineage_id)}
                    className="text-pollen"
                  >
                    {regenBusyLineage === row.lineage_id ? "Regenerating…" : "Regenerate"}
                  </NeonButton>
                </div>
                {open && detail ? (
                  <div className="space-y-3 border-t border-cyan/[0.06] pt-4">
                    <pre className="max-h-[min(52vh,480px)] overflow-auto whitespace-pre-wrap rounded-xl border border-cyan/[0.08] bg-[#050510]/90 p-3 font-[family-name:var(--font-jetbrains)] text-[12px] text-[#eaeaf2]">
                      {detail.markdown_body}
                    </pre>
                    {detail.voice_script ? (
                      <div>
                        <p className="mb-1 font-[family-name:var(--font-poppins)] text-[10px] uppercase tracking-[0.16em] text-zinc-500">
                          SECTION_VOICE (preview)
                        </p>
                        <p className="rounded-xl border border-cyan/[0.08] bg-black/35 p-3 font-[family-name:var(--font-poppins)] text-sm text-zinc-200">
                          {detail.voice_script.slice(0, 1200)}
                          {detail.voice_script.length > 1200 ? "…" : ""}
                        </p>
                      </div>
                    ) : null}
                    <details className="rounded-xl border border-cyan/[0.08] bg-black/20 p-3">
                      <summary className="cursor-pointer font-[family-name:var(--font-poppins)] text-xs font-semibold text-data">
                        Structured JSON
                      </summary>
                      <pre className="mt-2 max-h-48 overflow-auto font-[family-name:var(--font-jetbrains)] text-[11px] text-zinc-300">
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
        <p className="text-center font-[family-name:var(--font-poppins)] text-sm text-muted-foreground">
          Nothing here yet — finish a Ballroom mission while logged into the cockpit to attach artefacts to your account.
        </p>
      ) : null}
    </div>
  );
}
