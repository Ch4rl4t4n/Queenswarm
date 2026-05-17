"use client";

import Link from "next/link";
import { Loader2Icon, SearchIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { HivePageHeader } from "@/components/hive/hive-page-header";
import { NeonButton } from "@/components/ui/neon-button";
import { HiveApiError, hiveGet } from "@/lib/api";
import type { RecipeRow, RecipeSemanticHit } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface RecipesPageClientProps {
  readonly showHeader?: boolean;
}

/** Verified catalog + semantic recall + tag facets — mobile-first stacked layout. */
export function RecipesPageClient({ showHeader = true }: RecipesPageClientProps): JSX.Element {
  const [catalog, setCatalog] = useState<RecipeRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [needle, setNeedle] = useState("");
  const [debounced, setDebounced] = useState("");
  const [semanticHits, setSemanticHits] = useState<RecipeSemanticHit[]>([]);
  const [searchBusy, setSearchBusy] = useState(false);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(needle.trim()), 350);
    return () => window.clearTimeout(t);
  }, [needle]);

  useEffect(() => {
    let cancelled = false;
    void hiveGet<RecipeRow[]>("recipes?verified_only=true&limit=120")
      .then((rows) => {
        if (!cancelled) {
          setCatalog(rows);
          setErr(null);
        }
      })
      .catch((e) => {
        if (!cancelled) setErr(e instanceof HiveApiError ? e.message : "Recipe catalog unavailable.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!debounced) {
      setSemanticHits([]);
      return;
    }
    let cancelled = false;
    setSearchBusy(true);
    void hiveGet<RecipeSemanticHit[]>(`recipes/search?q=${encodeURIComponent(debounced)}&limit=24`)
      .then((hits) => {
        if (!cancelled) setSemanticHits(hits);
      })
      .catch(() => {
        if (!cancelled) setSemanticHits([]);
      })
      .finally(() => {
        if (!cancelled) setSearchBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [debounced]);

  const allTags = useMemo(() => {
    const s = new Set<string>();
    for (const r of catalog) {
      for (const t of r.topic_tags ?? []) {
        if (t.trim()) s.add(t.trim());
      }
    }
    return [...s].sort((a, b) => a.localeCompare(b));
  }, [catalog]);

  const toggleTag = useCallback((tag: string) => {
    setSelectedTags((prev) => (prev.includes(tag) ? prev.filter((x) => x !== tag) : [...prev, tag]));
  }, []);

  const filteredCatalog = useMemo(() => {
    if (!selectedTags.length) return catalog;
    return catalog.filter((r) => selectedTags.every((t) => (r.topic_tags ?? []).includes(t)));
  }, [catalog, selectedTags]);

  const showingSemantic = Boolean(debounced);

  return (
    <div className="space-y-8">
      {showHeader ? (
        <HivePageHeader
          title="Recipe Library"
          subtitle="Verified workflows · Chroma semantic recall · topic tag facets"
          actions={
            <NeonButton asChild variant="primary" className="uppercase tracking-[0.12em] touch-manipulation min-h-[44px]">
              <Link href="/tasks/new">Run mission</Link>
            </NeonButton>
          }
        />
      ) : (
        <div className="flex items-center justify-between gap-2 rounded-2xl border border-cyan/20 bg-black/25 px-3 py-2">
          <p className="font-[family-name:var(--font-poppins)] text-xs uppercase tracking-[0.16em] text-cyan">Saved recipes</p>
          <NeonButton asChild variant="ghost" className="min-h-[36px] text-xs uppercase tracking-[0.1em]">
            <Link href="/tasks/new">Run mission</Link>
          </NeonButton>
        </div>
      )}

      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="relative flex-1">
          <SearchIcon className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" aria-hidden />
          <input
            type="search"
            value={needle}
            onChange={(e) => setNeedle(e.target.value)}
            placeholder="Semantic search (natural language)…"
            className="min-h-[48px] w-full rounded-xl border border-cyan/[0.14] bg-hive-card/90 py-3 pl-11 pr-4 font-[family-name:var(--font-poppins)] text-sm text-[#fafafa] placeholder:text-zinc-500 focus:border-pollen/35 focus:outline-none"
          />
          {searchBusy ? (
            <Loader2Icon className="absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-cyan" aria-hidden />
          ) : null}
        </div>
        <p className="font-[family-name:var(--font-poppins)] text-xs text-zinc-500 lg:max-w-xs lg:text-right">
          Desktop: keep search + catalog visible together. Mobile: scroll tags → grid — minimal context switching.
        </p>
      </div>

      <div className="rounded-2xl border border-cyan/[0.08] bg-black/35 p-3">
        <p className="mb-2 px-2 font-mono text-[10px] uppercase tracking-[0.28em] text-zinc-600">Topic tags</p>
        <div className="flex flex-wrap gap-2">
          {allTags.map((tag) => {
            const on = selectedTags.includes(tag);
            return (
              <button
                key={tag}
                type="button"
                onClick={() => toggleTag(tag)}
                className={cn(
                  "min-h-[36px] rounded-full border px-3 py-1.5 font-[family-name:var(--font-poppins)] text-xs transition touch-manipulation",
                  on ? "border-pollen/55 bg-pollen/15 text-pollen" : "border-zinc-700 text-zinc-400 hover:border-cyan/25",
                )}
              >
                #{tag}
              </button>
            );
          })}
          {!allTags.length ? <span className="text-xs text-zinc-500">No tags in catalog slice.</span> : null}
        </div>
      </div>

      {err ? (
        <p className="rounded-xl border border-danger/35 bg-black/50 px-4 py-3 font-[family-name:var(--font-poppins)] text-sm text-danger">{err}</p>
      ) : null}

      {loading ? (
        <p className="flex items-center gap-2 font-[family-name:var(--font-poppins)] text-sm text-zinc-400">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading catalog…
        </p>
      ) : null}

      <section>
        <h2 className="mb-4 font-[family-name:var(--font-poppins)] text-sm font-semibold uppercase tracking-[0.2em] text-cyan">
          {showingSemantic ? "Semantic hits" : `Catalog · ${filteredCatalog.length} recipes`}
        </h2>

        {showingSemantic ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {semanticHits.map((hit) => (
              <article
                key={hit.chroma_document_id}
                className="flex flex-col gap-3 rounded-[22px] border border-cyan/[0.09] bg-hive-card/95 p-5 shadow-[inset_0_0_0_1px_rgb(0_255_255/0.04)]"
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#fafafa]">
                    {hit.postgres_row?.name ?? "Embedding (unlink)"}
                  </h3>
                  <span className="shrink-0 rounded-full border border-cyan/35 px-2 py-0.5 font-mono text-[11px] text-cyan">
                    {(hit.similarity * 100).toFixed(1)}%
                  </span>
                </div>
                <p className="line-clamp-4 font-[family-name:var(--font-poppins)] text-xs text-zinc-400">{hit.document_preview || "—"}</p>
              </article>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {filteredCatalog.map((recipe) => (
              <article
                key={recipe.id}
                className={cn(
                  "flex flex-col gap-4 rounded-[22px] border border-cyan/[0.09] bg-hive-card/95 p-5 shadow-[inset_0_0_0_1px_rgb(0_255_255/0.04)] transition hover:border-pollen/25",
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="font-[family-name:var(--font-poppins)] text-[10px] uppercase tracking-[0.15em] text-zinc-500">
                    {recipe.verified_at ? "verified" : "draft"}
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full border border-pollen/55 px-2 py-1 font-[family-name:var(--font-poppins)] text-[11px] text-pollen">
                    ★ wins {recipe.success_count ?? 0}
                  </span>
                </div>
                <div>
                  <h2 className="font-[family-name:var(--font-poppins)] text-xl font-semibold text-[#fafafa]">{recipe.name}</h2>
                  {(recipe.topic_tags ?? []).length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {(recipe.topic_tags ?? []).map((t) => (
                        <span key={t} className="rounded-full bg-black/40 px-2 py-0.5 font-[family-name:var(--font-poppins)] text-[10px] text-zinc-500">
                          #{t}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
                <dl className="grid grid-cols-3 gap-2 font-[family-name:var(--font-poppins)] text-sm">
                  <div>
                    <dt className="font-[family-name:var(--font-poppins)] text-[10px] uppercase tracking-[0.16em] text-zinc-500">Fails</dt>
                    <dd className="mt-1 tabular-nums text-[#fafafa]">{recipe.fail_count ?? 0}</dd>
                  </div>
                  <div>
                    <dt className="font-[family-name:var(--font-poppins)] text-[10px] uppercase tracking-[0.16em] text-zinc-500">Avg pollen</dt>
                    <dd className="mt-1 tabular-nums text-data">{Math.round(recipe.avg_pollen_earned ?? 0)}</dd>
                  </div>
                  <div>
                    <dt className="font-[family-name:var(--font-poppins)] text-[10px] uppercase tracking-[0.16em] text-zinc-500">ID</dt>
                    <dd className="mt-1 truncate font-mono text-[10px] text-zinc-500">{recipe.id.slice(0, 8)}…</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        )}

        {!loading && !showingSemantic && filteredCatalog.length === 0 ? (
          <p className="text-center font-[family-name:var(--font-poppins)] text-sm text-muted-foreground">
            No recipes match selected tags — clear chips or widen catalog limits.
          </p>
        ) : null}
        {showingSemantic && !semanticHits.length && !searchBusy ? (
          <p className="text-center font-[family-name:var(--font-poppins)] text-sm text-muted-foreground">No semantic hits — tweak wording.</p>
        ) : null}
      </section>
    </div>
  );
}
