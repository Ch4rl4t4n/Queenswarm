"use client";

import { Loader2Icon, SparklesIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { V4Chip } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface SkillCatalogItem {
  slug: string;
  title: string;
  keywords: string[];
  roles: string[];
  is_builtin: boolean;
  is_tenant: boolean;
}

export interface SkillPickerChipsProps {
  selected: string[];
  onChange: (slugs: string[]) => void;
  suggested?: string[];
  className?: string;
}

/** Multi-select skill chips for session dispatch — builtin + tenant Skill Factory rows. */
export function SkillPickerChips({
  selected,
  onChange,
  suggested = [],
  className,
}: SkillPickerChipsProps): JSX.Element {
  const [catalog, setCatalog] = useState<SkillCatalogItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const rows = await hiveGet<SkillCatalogItem[]>("skill-factory/catalog");
      setCatalog(rows);
    } catch (e) {
      if (e instanceof HiveApiError && e.status === 404) {
        setCatalog([]);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const mergedSlugs = useMemo(() => {
    const seen = new Set<string>();
    const out: string[] = [];
    for (const slug of [...suggested, ...selected, ...catalog.map((row) => row.slug)]) {
      const key = slug.trim().toLowerCase();
      if (!key || seen.has(key)) continue;
      seen.add(key);
      out.push(key);
    }
    return out.slice(0, 40);
  }, [catalog, selected, suggested]);

  const toggle = (slug: string): void => {
    const key = slug.toLowerCase();
    if (selected.map((s) => s.toLowerCase()).includes(key)) {
      onChange(selected.filter((s) => s.toLowerCase() !== key));
      return;
    }
    onChange([...selected, key]);
  };

  if (loading && catalog.length === 0) {
    return (
      <p className={cn("flex items-center gap-2 text-xs text-(--qs-text-4)", className)}>
        <Loader2Icon className="size-3.5 animate-spin" aria-hidden />
        Loading skills…
      </p>
    );
  }

  if (mergedSlugs.length === 0) {
    return (
      <p className={cn("text-xs text-(--qs-text-4)", className)}>
        Skills auto-selected from goal — enable Skill Factory for custom library.
      </p>
    );
  }

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex flex-wrap items-center gap-2">
        <SparklesIcon className="size-3.5 text-pollen" aria-hidden />
        <span className="text-[11px] font-medium uppercase tracking-wider text-(--qs-text-3)">
          Skills override (optional)
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {mergedSlugs.map((slug) => {
          const active = selected.map((s) => s.toLowerCase()).includes(slug);
          const row = catalog.find((item) => item.slug === slug);
          const suggestedHit = suggested.includes(slug);
          return (
            <button
              key={slug}
              type="button"
              aria-pressed={active}
              className={cn(
                "rounded-full border px-2.5 py-0.5 text-[11px] font-mono transition",
                active
                  ? "border-pollen/60 bg-pollen/15 text-pollen"
                  : "border-white/15 bg-black/20 text-(--qs-text-3) hover:border-cyan/40",
              )}
              onClick={() => toggle(slug)}
            >
              {row?.title ?? slug}
              {row?.is_tenant ? (
                <V4Chip className="ml-1 inline text-[9px]">factory</V4Chip>
              ) : null}
              {!active && suggestedHit ? (
                <span className="ml-1 text-cyan">· suggested</span>
              ) : null}
            </button>
          );
        })}
      </div>
      <p className="text-[10px] text-(--qs-text-4)">
        Empty selection = auto match from goal. Pinned chips pass explicit <code>skills</code> to the session.
      </p>
    </div>
  );
}
