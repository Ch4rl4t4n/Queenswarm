"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { InfoHint } from "@/components/hive/info-hint";
import { cn } from "@/lib/utils";
import { filterSectionNavItems, sectionDensityClass, type SectionDensity } from "@/lib/section-hub";
import {
  readStoredSectionDensityFromBrowser,
  resolveSectionDensity,
  saveStoredSectionDensityFromBrowser,
} from "@/lib/section-hub-preferences";

export interface SectionNavItem {
  readonly href: string;
  readonly title: string;
  readonly description: string;
}

interface SectionNavGridProps {
  readonly items: SectionNavItem[];
  readonly showHints?: boolean;
}

export function SectionNavGrid({ items, showHints = true }: SectionNavGridProps): JSX.Element {
  const [query, setQuery] = useState("");
  const [density, setDensity] = useState<SectionDensity>("comfortable");

  useEffect(() => {
    setDensity(readStoredSectionDensityFromBrowser());
  }, []);

  useEffect(() => {
    saveStoredSectionDensityFromBrowser(resolveSectionDensity(density));
  }, [density]);

  const filteredItems = useMemo(() => filterSectionNavItems(items, query), [items, query]);
  const quickItems = items.slice(0, 3);
  const densityClass = sectionDensityClass(density);

  return (
    <div className="space-y-4">
      <div className="sticky top-16 z-20 rounded-2xl border border-cyan/20 bg-[#070714]/95 p-3 backdrop-blur">
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <label className="flex min-w-0 flex-1 items-center rounded-xl border border-cyan/20 bg-black/30 px-3 py-2">
              <span className="sr-only">Filter section links</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Filter links..."
                className="w-full bg-transparent text-sm text-zinc-100 outline-none placeholder:text-zinc-500"
              />
            </label>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setDensity("comfortable")}
                aria-label="Cozy density"
                className={cn(
                  "rounded-lg border px-3 py-1 text-xs",
                  density === "comfortable"
                    ? "border-pollen/60 bg-pollen/15 text-pollen"
                    : "border-zinc-700 text-zinc-300",
                )}
              >
                Cozy
              </button>
              <button
                type="button"
                onClick={() => setDensity("compact")}
                aria-label="Compact density"
                className={cn(
                  "rounded-lg border px-3 py-1 text-xs",
                  density === "compact" ? "border-pollen/60 bg-pollen/15 text-pollen" : "border-zinc-700 text-zinc-300",
                )}
              >
                Compact
              </button>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {quickItems.map((item) => (
              <Link
                key={`quick-${item.href}`}
                href={item.href}
                className="rounded-lg border border-zinc-700/80 px-2.5 py-1 text-xs text-zinc-300 transition hover:border-pollen/40 hover:text-pollen"
                prefetch
              >
                {item.title}
              </Link>
            ))}
            {query ? (
              <button
                type="button"
                onClick={() => setQuery("")}
                className="rounded-lg border border-cyan/30 px-2.5 py-1 text-xs text-cyan transition hover:border-cyan/60"
              >
                Clear
              </button>
            ) : null}
          </div>
        </div>
      </div>

      {filteredItems.length === 0 ? (
        <div className="rounded-2xl border border-zinc-800 bg-black/20 p-4 text-sm text-zinc-400">
          No matches in this section. Try a shorter query.
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {filteredItems.map((item) => (
          <article
            key={item.href}
            className={cn(
              "group rounded-2xl border border-cyan/20 bg-black/25 transition hover:border-pollen/40 hover:bg-black/35",
              densityClass,
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <Link href={item.href} className="font-(family-name:--font-poppins) text-sm font-semibold text-zinc-100 group-hover:text-pollen" prefetch>
                {item.title}
              </Link>
              {showHints ? (
                <InfoHint
                  title={item.title}
                  description={item.description}
                  options={["Open section", "Review details", "Execute action"]}
                />
              ) : null}
            </div>
            <p className="mt-1 text-xs text-zinc-400">{item.description}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
