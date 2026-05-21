"use client";

import { InfoHint } from "@/components/hive/info-hint";
import { V4Badge } from "@/components/ui/v4";
import type { RecipeMatchConfigPayload, RecipeSemanticHit } from "@/lib/hive-types";
import {
  formatSimilarityPct,
  hybridSummary,
  isRecipeMatchEligible,
  primarySimilarity,
  recipeMatchTone,
  vectorSimilarity,
} from "@/lib/recipe-match-utils";
import { cn } from "@/lib/utils";

interface RecipeCosineThresholdBannerProps {
  config: RecipeMatchConfigPayload;
  hitCount: number;
}

/** Explains the 0.85 imitation gate and hybrid scoring weights. */
export function RecipeCosineThresholdBanner({ config, hitCount }: RecipeCosineThresholdBannerProps): JSX.Element {
  const thresholdPct = formatSimilarityPct(config.match_threshold);

  return (
    <div className="rounded-xl border border-cyan/25 bg-cyan/5 px-4 py-3 text-sm text-(--qs-text-2)">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-(--qs-text)">Imitation gate</span>
        <V4Badge tone="info">≥ {thresholdPct}</V4Badge>
        <span className="text-xs text-(--qs-text-3)">{hybridSummary(config)}</span>
        <InfoHint
          title="Recipe cosine matching"
          description="Workflow breaker and task preview auto-match verified recipes when hybrid similarity meets the gate."
          options={[
            `Threshold default: ${thresholdPct}`,
            "Vector cosine from Chroma embeddings",
            "Graph signal blends success rate + imitation edges",
          ]}
        />
      </div>
      <p className="mt-2 text-xs text-(--qs-text-3)">
        {hitCount} semantic hit{hitCount === 1 ? "" : "s"} · scores below {thresholdPct} are shown for transparency but
        won&apos;t auto-bind workflows.
      </p>
    </div>
  );
}

interface RecipeSemanticHitCardProps {
  hit: RecipeSemanticHit;
  config: RecipeMatchConfigPayload;
}

/** Single semantic hit with cosine bar vs 0.85 threshold. */
export function RecipeSemanticHitCard({ hit, config }: RecipeSemanticHitCardProps): JSX.Element {
  const score = primarySimilarity(hit);
  const vector = vectorSimilarity(hit);
  const eligible = isRecipeMatchEligible(score, config.match_threshold);
  const barPct = Math.round(Math.min(100, score * 100));
  const thresholdPct = Math.round(config.match_threshold * 100);

  return (
    <article className="v4-dream-cycle-card flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-lg font-semibold text-(--qs-text)">{hit.postgres_row?.name ?? "Embedding (unlink)"}</h3>
        <V4Badge tone={recipeMatchTone(score, config.match_threshold)}>
          {formatSimilarityPct(score)}
        </V4Badge>
      </div>

      <div className="relative h-2 overflow-hidden rounded-full bg-white/10">
        <div
          className={cn("h-full rounded-full transition-all", eligible ? "bg-success" : "bg-pollen")}
          style={{ width: `${barPct}%` }}
        />
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-cyan shadow-[0_0_6px_rgba(0,255,255,0.8)]"
          style={{ left: `${thresholdPct}%` }}
          aria-hidden
        />
      </div>

      <div className="flex flex-wrap gap-2 text-[11px] text-(--qs-text-3)">
        <span className={eligible ? "text-success" : "text-(--qs-magenta)"}>
          {eligible ? "Auto-match eligible" : "Below imitation gate"}
        </span>
        {vector != null ? <span>Vector {formatSimilarityPct(vector)}</span> : null}
        {typeof hit.graph_score === "number" ? <span>Graph {formatSimilarityPct(hit.graph_score)}</span> : null}
      </div>

      <p className="line-clamp-4 text-xs text-(--qs-text-3)">{hit.document_preview || "—"}</p>
    </article>
  );
}

interface RecipeSemanticHitRowProps {
  hit: RecipeSemanticHit;
  config: RecipeMatchConfigPayload;
}

/** Compact list row for learning console semantic recall. */
export function RecipeSemanticHitRow({ hit, config }: RecipeSemanticHitRowProps): JSX.Element {
  const score = primarySimilarity(hit);
  const eligible = isRecipeMatchEligible(score, config.match_threshold);
  const barPct = Math.round(Math.min(100, score * 100));
  const thresholdPct = Math.round(config.match_threshold * 100);

  return (
    <li className="rounded-(--qs-radius-sm) border border-(--qs-border) bg-white/[0.04] p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-(--qs-amber)">{hit.postgres_row?.name ?? "Unlinked embedding"}</p>
        <V4Badge tone={recipeMatchTone(score, config.match_threshold)}>{formatSimilarityPct(score)}</V4Badge>
      </div>
      <div className="relative mt-2 h-1.5 overflow-hidden rounded-full bg-white/10">
        <div
          className={cn("h-full rounded-full", eligible ? "bg-success" : "bg-pollen")}
          style={{ width: `${barPct}%` }}
        />
        <div className="absolute top-0 bottom-0 w-px bg-cyan/80" style={{ left: `${thresholdPct}%` }} aria-hidden />
      </div>
      <p className="mt-1 text-[10px] text-(--qs-text-3)">
        {eligible ? "Auto-match eligible" : `Below ${formatSimilarityPct(config.match_threshold)} gate`}
      </p>
      <p className="mt-1 line-clamp-2 text-xs text-(--qs-text-3)">{hit.document_preview || "—"}</p>
    </li>
  );
}
