"use client";

import { ChevronDownIcon, Loader2Icon, SparklesIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { HiveSwitch } from "@/components/ui/hive-switch";
import { V4Chip } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import {
  pickCompactSkillSlugs,
  readSkillUsageMap,
  recordSkillUsage,
  sortCatalogForPicker,
  type SkillCatalogItem,
} from "@/lib/skill-picker-catalog";
import { cn } from "@/lib/utils";

export type { SkillCatalogItem };

export interface SkillPickerChipsProps {
  selected: string[];
  onChange: (slugs: string[]) => void;
  suggested?: string[];
  className?: string;
  /** When true, backend auto-matches skills from goal (default). */
  autoMatch?: boolean;
  onAutoMatchChange?: (enabled: boolean) => void;
}

function SkillChipButton({
  slug,
  title,
  active,
  isTenant,
  suggestedHit,
  onToggle,
}: {
  slug: string;
  title: string;
  active: boolean;
  isTenant: boolean;
  suggestedHit: boolean;
  onToggle: (slug: string) => void;
}): JSX.Element {
  return (
    <button
      type="button"
      aria-pressed={active}
      className={cn(
        "rounded-full border px-2.5 py-0.5 text-[11px] font-mono transition",
        active
          ? "border-pollen/60 bg-pollen/15 text-pollen"
          : "border-white/15 bg-black/20 text-(--qs-text-3) hover:border-cyan/40",
      )}
      onClick={() => onToggle(slug)}
    >
      {title}
      {isTenant ? <V4Chip className="ml-1 inline text-[9px]">factory</V4Chip> : null}
      {!active && suggestedHit ? <span className="ml-1 text-cyan">· suggested</span> : null}
    </button>
  );
}

/** Multi-select skill picker — auto-match switch + compact favorites + expandable full catalog. */
export function SkillPickerChips({
  selected,
  onChange,
  suggested = [],
  className,
  autoMatch: autoMatchProp,
  onAutoMatchChange,
}: SkillPickerChipsProps): JSX.Element {
  const [catalog, setCatalog] = useState<SkillCatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [autoMatchInternal, setAutoMatchInternal] = useState(true);
  const [allExpanded, setAllExpanded] = useState(false);
  const [usageVersion, setUsageVersion] = useState(0);

  const autoMatch = autoMatchProp ?? autoMatchInternal;
  const setAutoMatch = onAutoMatchChange ?? setAutoMatchInternal;

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

  const usage = useMemo(() => readSkillUsageMap(), [usageVersion]);

  const sortedCatalog = useMemo(() => sortCatalogForPicker(catalog, usage), [catalog, usage]);

  const compactSlugs = useMemo(
    () =>
      pickCompactSkillSlugs({
        catalog,
        selected,
        suggested,
        usage,
      }),
    [catalog, selected, suggested, usage],
  );

  const hiddenCount = Math.max(0, sortedCatalog.length - compactSlugs.length);

  const toggle = (slug: string): void => {
    const key = slug.toLowerCase();
    const next = selected.map((s) => s.toLowerCase()).includes(key)
      ? selected.filter((s) => s.toLowerCase() !== key)
      : [...selected, key];
    onChange(next);
    if (next.length > 0) {
      recordSkillUsage(next);
      setUsageVersion((value) => value + 1);
    }
  };

  const handleAutoMatchChange = (enabled: boolean): void => {
    setAutoMatch(enabled);
    if (enabled) {
      onChange([]);
      setAllExpanded(false);
      return;
    }
  };

  const catalogBySlug = useMemo(() => new Map(catalog.map((row) => [row.slug.toLowerCase(), row])), [catalog]);

  const renderSlugChip = (slug: string): JSX.Element | null => {
    const row = catalogBySlug.get(slug.toLowerCase());
    if (!row) {
      return null;
    }
    const active = selected.map((s) => s.toLowerCase()).includes(slug.toLowerCase());
    return (
      <SkillChipButton
        key={slug}
        slug={slug}
        title={row.title}
        active={active}
        isTenant={row.is_tenant}
        suggestedHit={suggested.includes(slug)}
        onToggle={toggle}
      />
    );
  };

  if (loading && catalog.length === 0) {
    return (
      <p className={cn("flex items-center gap-2 text-xs text-(--qs-text-4)", className)}>
        <Loader2Icon className="size-3.5 animate-spin" aria-hidden />
        Loading skills…
      </p>
    );
  }

  return (
    <div className={cn("space-y-2 rounded-xl border border-white/8 bg-black/15 p-3", className)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <SparklesIcon className="size-3.5 text-pollen" aria-hidden />
          <span className="text-[11px] font-medium uppercase tracking-wider text-(--qs-text-3)">Skills</span>
        </div>
        <label className="flex items-center gap-2 text-[11px] text-(--qs-text-3)">
          <HiveSwitch checked={autoMatch} onCheckedChange={handleAutoMatchChange} aria-label="Auto-assign skills" />
          Auto-assign from catalog
        </label>
      </div>

      {autoMatch ? (
        <p className="text-[11px] leading-relaxed text-(--qs-text-4)">
          Queen matches skills from your goal and the built-in library. Turn off to pin specific skills manually.
        </p>
      ) : null}

      {!autoMatch ? (
        <>
          <div className="flex flex-wrap gap-1.5">
            {compactSlugs.map((slug) => renderSlugChip(slug))}
          </div>

          {hiddenCount > 0 ? (
            <button
              type="button"
              className="flex items-center gap-1 text-[11px] text-cyan hover:underline"
              aria-expanded={allExpanded}
              onClick={() => setAllExpanded((open) => !open)}
            >
              <ChevronDownIcon className={cn("size-3.5 transition", allExpanded && "rotate-180")} aria-hidden />
              {allExpanded ? "Hide full catalog" : `Show all skills (${sortedCatalog.length})`}
            </button>
          ) : null}

          {allExpanded ? (
            <div className="max-h-48 overflow-y-auto rounded-lg border border-white/10 bg-black/25 p-2">
              <div className="flex flex-wrap gap-1.5">
                {sortedCatalog.map((row) => renderSlugChip(row.slug))}
              </div>
            </div>
          ) : null}

          <p className="text-[10px] text-(--qs-text-4)">
            Pinned chips pass explicit <code>skills</code> to the session. Factory skills appear when selected or in
            “Show all”.
          </p>
        </>
      ) : (
        <button
          type="button"
          className="text-[11px] text-(--qs-text-4) underline-offset-2 hover:text-cyan hover:underline"
          onClick={() => handleAutoMatchChange(false)}
        >
          Manual override…
        </button>
      )}
    </div>
  );
}
