"use client";

import Link from "next/link";
import { CreditCardIcon, DownloadIcon, ExternalLink, Loader2Icon } from "lucide-react";

import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { V4Badge, V4Chip } from "@/components/ui/v4";
import type { SkillCatalogRecipeItem } from "@/lib/hive-types";
import { useGridTwoRowPageSize } from "@/lib/use-grid-two-row-page-size";
import { usePaginatedSlice } from "@/lib/use-paginated-slice";
import { cn } from "@/lib/utils";

export interface RecipeSkillsGridProps {
  recipes: SkillCatalogRecipeItem[];
  loading?: boolean;
  sectionLabel: string;
  sectionBadge: string;
  checkoutAvailable: boolean;
  exportBusyId: string | null;
  checkoutBusyId: string | null;
  onAction: (recipe: SkillCatalogRecipeItem) => void;
  emphasizePremium?: boolean;
  emptyMessage?: string;
}

function primaryCategory(recipe: SkillCatalogRecipeItem): string {
  const tag = recipe.topic_tags?.[0];
  if (tag) return tag.replaceAll("_", " ");
  return "verified recipe";
}

function recipeAgentUsage(recipe: SkillCatalogRecipeItem): string {
  const tags = (recipe.topic_tags ?? []).slice(0, 5).join(", ");
  if (recipe.description?.trim()) {
    const lead = recipe.description.trim();
    return tags
      ? `${lead} Swarm lanes match on: ${tags}.`
      : `${lead} Export as SKILL.md + HIVE.md for Cursor or Claude.`;
  }
  return tags
    ? `Swarm replays this verified workflow when topics match: ${tags}. Export bundles portable skill shards for external agents.`
    : `Export verified recipe \`${recipe.slug}\` as a portable skill bundle with pollen-verified success metrics.`;
}

function recipeSummary(recipe: SkillCatalogRecipeItem): string {
  if (recipe.description?.trim()) return recipe.description.trim();
  return `Verified workflow with ${(recipe.success_rate * 100).toFixed(0)}% success rate and ${Math.round(recipe.avg_pollen_earned)} avg pollen.`;
}

function successTone(rate: number): "ok" | "warn" | "info" {
  if (rate >= 0.85) return "ok";
  if (rate >= 0.6) return "warn";
  return "info";
}

function recipeStatusBadge(recipe: SkillCatalogRecipeItem): { label: string; tone: "ok" | "warn" | "err" | "info" | "gold" | "purple" } {
  const lockedPremium = recipe.premium && !recipe.unlocked;
  const isStarterTier = lockedPremium && (recipe.price_eur_cents ?? 0) <= 900;
  if (recipe.ugc) return { label: "community", tone: "purple" };
  if (isStarterTier) return { label: "starter", tone: "ok" };
  if (lockedPremium) return { label: "locked", tone: "warn" };
  if (recipe.premium && recipe.unlocked) return { label: "unlocked", tone: "ok" };
  return { label: "verified", tone: "info" };
}

function RecipeSkillMarketCard({
  recipe,
  checkoutAvailable,
  exportBusyId,
  checkoutBusyId,
  onAction,
  emphasizePremium = false,
}: {
  recipe: SkillCatalogRecipeItem;
  checkoutAvailable: boolean;
  exportBusyId: string | null;
  checkoutBusyId: string | null;
  onAction: (recipe: SkillCatalogRecipeItem) => void;
  emphasizePremium?: boolean;
}): JSX.Element {
  const lockedPremium = recipe.premium && !recipe.unlocked;
  const busy = exportBusyId === recipe.id || checkoutBusyId === recipe.id;
  const isStarterTier = lockedPremium && (recipe.price_eur_cents ?? 0) <= 900;
  const status = recipeStatusBadge(recipe);
  const successPct = Math.round(recipe.success_rate * 100);

  return (
    <article
      className={cn(
        "v4-dream-cycle-card flex h-full min-w-0 flex-col gap-3",
        emphasizePremium &&
          lockedPremium &&
          (isStarterTier
            ? "ring-2 ring-(--qs-green)/50 shadow-[0_0_28px_rgba(0,255,136,0.15)]"
            : "ring-1 ring-pollen/40 shadow-[0_0_24px_rgba(255,184,0,0.12)]"),
      )}
    >
      <div className="flex min-w-0 items-start justify-between gap-2">
        <div className="min-w-0 flex-1 space-y-1">
          <p className="qs-card-title text-sm font-semibold text-(--qs-text)">{recipe.name}</p>
          <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">
            {primaryCategory(recipe)}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
          <V4Badge tone={status.tone}>{status.label}</V4Badge>
        </div>
      </div>

      <p className="qs-card-body line-clamp-3 text-xs leading-relaxed text-(--qs-text-3)">{recipeSummary(recipe)}</p>

      <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-3 py-2">
        <p className="v4-field-label text-[10px] text-cyan-300/90">How agents use this</p>
        <p className="qs-card-body mt-1 text-xs leading-relaxed text-(--qs-text-2)">{recipeAgentUsage(recipe)}</p>
      </div>

      <p className="qs-card-meta font-mono text-[11px] text-(--qs-text-3)">
        {recipe.slug} · ★ {successPct}% · pollen {Math.round(recipe.avg_pollen_earned)}
      </p>

      <div className="qs-tag-row">
        <V4Badge tone={successTone(recipe.success_rate)}>{successPct}% success</V4Badge>
        {recipe.avg_pollen_earned >= 10 ? <V4Badge tone="gold">high pollen</V4Badge> : null}
        {(recipe.topic_tags ?? []).slice(0, 4).map((tag) => (
          <V4Chip key={tag} type="span" variant="tag" title={tag}>
            {tag.replaceAll("_", " ")}
          </V4Chip>
        ))}
      </div>

      {lockedPremium ? (
        <p className={cn("qs-card-body text-xs font-medium", isStarterTier ? "text-(--qs-green)" : "text-pollen")}>
          €{((recipe.price_eur_cents ?? 0) / 100).toFixed(2)} one-time unlock
          {recipe.ugc && recipe.platform_cut_bps ? (
            <span className="text-(--qs-text-3)"> · community skill</span>
          ) : null}
        </p>
      ) : null}

      <Link
        href={`/recipes?needle=${encodeURIComponent(recipe.slug)}`}
        className="inline-flex items-center gap-1.5 text-xs text-pollen hover:underline"
      >
        <ExternalLink className="h-3.5 w-3.5 shrink-0" aria-hidden />
        Recipe library
      </Link>

      <div className="v4-dream-cycle-card-actions">
        <button
          type="button"
          className={cn(
            "qs-btn qs-btn--sm min-w-[5.5rem]",
            lockedPremium && checkoutAvailable ? "qs-btn--primary" : lockedPremium ? "qs-btn--ghost opacity-70" : "qs-btn--primary",
          )}
          disabled={busy || (lockedPremium && !checkoutAvailable)}
          title={lockedPremium && !checkoutAvailable ? "Premium checkout removed on this server" : undefined}
          onClick={() => onAction(recipe)}
        >
          {busy ? (
            <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden />
          ) : lockedPremium ? (
            <CreditCardIcon className="h-3.5 w-3.5 shrink-0" aria-hidden />
          ) : (
            <DownloadIcon className="h-3.5 w-3.5 shrink-0" aria-hidden />
          )}
          {lockedPremium ? (checkoutAvailable ? "Unlock" : "Locked") : "Export"}
        </button>
      </div>
    </article>
  );
}

/** Verified recipe skills — marketplace-style cards with pagination. */
export function RecipeSkillsGrid({
  recipes,
  loading = false,
  sectionLabel,
  sectionBadge,
  checkoutAvailable,
  exportBusyId,
  checkoutBusyId,
  onAction,
  emphasizePremium = false,
  emptyMessage,
}: RecipeSkillsGridProps): JSX.Element | null {
  const pageSize = useGridTwoRowPageSize({ columns: 2 });
  const pagination = usePaginatedSlice(
    recipes,
    pageSize,
    `${pageSize}|${recipes.length}|${loading}|${sectionLabel}`,
  );

  if (!loading && !recipes.length) {
    return emptyMessage ? <p className="mt-3 text-sm text-(--qs-text-3)">{emptyMessage}</p> : null;
  }

  return (
    <div className="recipe-skills-grid-wrap mt-4 min-w-0 space-y-3">
      <div className="hub-catalog-section-head flex flex-wrap items-center gap-2">
        <p className="hub-catalog-section-head__label">{sectionLabel}</p>
        <V4Badge tone="info">{loading ? "loading…" : sectionBadge}</V4Badge>
      </div>

      <ViewportBoundedPanel
        className="v4-recipe-catalog-panel recipe-skills-grid-panel"
        footer={
          !loading && recipes.length > 0 ? (
            <ListPaginator
              page={pagination.page}
              totalPages={pagination.totalPages}
              totalItems={pagination.totalItems}
              pageSize={pageSize}
              onPageChange={pagination.setPage}
            />
          ) : null
        }
      >
        <div className="hub-catalog-grid">
          {loading
            ? Array.from({ length: 4 }, (_, index) => (
                <article
                  key={`recipe-skel-${sectionLabel}-${index}`}
                  className="v4-dream-cycle-card animate-pulse"
                  aria-hidden
                >
                  <div className="h-4 w-48 rounded bg-white/15" />
                  <div className="mt-3 h-3 w-full rounded bg-white/10" />
                  <div className="mt-2 h-16 w-full rounded bg-white/10" />
                  <div className="mt-4 h-8 w-24 rounded bg-white/10" />
                </article>
              ))
            : pagination.slice.map((recipe) => (
                <RecipeSkillMarketCard
                  key={recipe.id}
                  recipe={recipe}
                  checkoutAvailable={checkoutAvailable}
                  exportBusyId={exportBusyId}
                  checkoutBusyId={checkoutBusyId}
                  onAction={onAction}
                  emphasizePremium={emphasizePremium}
                />
              ))}
        </div>
      </ViewportBoundedPanel>
    </div>
  );
}
