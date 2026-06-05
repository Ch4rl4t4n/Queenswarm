"use client";

import {
  ArchiveIcon,
  BanIcon,
  DownloadIcon,
  GitBranchIcon,
  Loader2Icon,
  RefreshCwIcon,
  RocketIcon,
  SparklesIcon,
  StoreIcon,
} from "lucide-react";

import { V4Badge } from "@/components/ui/v4";
import { cn } from "@/lib/utils";

export interface FactoryLibrarySkillRow {
  id: string;
  slug: string;
  title: string;
  description: string;
  sellable_tier: string;
  sellable_score: number;
  sellable_issues: string[];
  github_exported_at: string | null;
  gumroad_product_id: string | null;
  gumroad_product_url: string | null;
  gumroad_published: boolean | null;
  factory_disposition: string | null;
  factory_attempt_count: number;
  factory_disposition_note: string | null;
}

function scorePct(score: number): string {
  return `${Math.round(score * 100)}%`;
}

function dispositionLabel(disposition: string | null): string | null {
  if (!disposition) return null;
  if (disposition === "worth_retry") return "worth retry";
  if (disposition === "deprioritized") return "deprioritized";
  if (disposition === "retired") return "retired";
  return disposition;
}

function dispositionTone(disposition: string | null): "ok" | "warn" | "err" | "info" | "purple" | "gold" {
  if (disposition === "worth_retry") return "ok";
  if (disposition === "deprioritized") return "warn";
  if (disposition === "retired") return "err";
  return "info";
}

function tierTone(tier: string): "ok" | "warn" | "err" | "info" | "purple" | "gold" {
  if (tier === "sellable") return "ok";
  if (tier === "draft") return "info";
  return "warn";
}

interface FactoryLibrarySkillCardProps {
  row: FactoryLibrarySkillRow;
  busyId: string | null;
  githubPrReady: boolean;
  gumroadListingReady: boolean;
  gumroadPublishReady: boolean;
  onSmartRebuild: (id: string) => void;
  onDeprioritize: (id: string) => void;
  onRetire: (id: string) => void;
  onEval: (id: string, title: string) => void;
  onExport: (id: string) => void;
  onGithubPr?: (id: string) => void;
  onGumroadDraft?: (id: string) => void;
  onGumroadPublish?: (id: string) => void;
}

export function FactoryLibrarySkillCard({
  row,
  busyId,
  githubPrReady,
  gumroadListingReady,
  gumroadPublishReady,
  onSmartRebuild,
  onDeprioritize,
  onRetire,
  onEval,
  onExport,
  onGithubPr,
  onGumroadDraft,
  onGumroadPublish,
}: FactoryLibrarySkillCardProps): JSX.Element {
  const busy = busyId === row.id;
  const rejected = row.sellable_tier === "rejected";
  const draft = row.sellable_tier === "draft";
  const canSmartRebuild = rejected || draft;
  const retired = row.factory_disposition === "retired";
  const dispLabel = dispositionLabel(row.factory_disposition);

  const issueSummary =
    row.sellable_issues.length > 0
      ? `Issues: ${row.sellable_issues.join(", ")}`
      : "Skill Factory session completed — review critic verdict and SKILL.md before publish.";

  return (
    <div className="v4-session-row v4-session-row--pollen" data-testid="factory-library-row">
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex flex-wrap items-center gap-2">
          <V4Badge tone={tierTone(row.sellable_tier)}>
            {row.sellable_tier} · {scorePct(row.sellable_score)}
          </V4Badge>
          <V4Badge tone={row.github_exported_at ? "ok" : "info"}>
            {row.github_exported_at ? "exported" : "ready"}
          </V4Badge>
          {dispLabel ? <V4Badge tone={dispositionTone(row.factory_disposition)}>{dispLabel}</V4Badge> : null}
          {row.factory_attempt_count > 0 ? (
            <V4Badge tone="purple">attempt {row.factory_attempt_count}</V4Badge>
          ) : null}
        </div>
        <p className="v4-session-goal text-sm font-medium text-(--qs-text)" title={row.title}>
          {row.title}
        </p>
        <p className="mt-1 font-mono text-[10px] text-pollen">{row.slug}</p>
        <p className="mt-2 text-xs text-(--qs-text-3)">
          {issueSummary}
          {row.factory_disposition_note ? (
            <span className="mt-1 block text-(--qs-text-4)">Note: {row.factory_disposition_note}</span>
          ) : null}
        </p>
        {canSmartRebuild ? (
          <p className="mt-2 text-[11px] text-cyan">
            Smart rebuild injects prior failures into factory goal — critic APPROVE + 3+ workflow steps required.
          </p>
        ) : null}
      </div>

      <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
        {canSmartRebuild ? (
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm gap-1"
            disabled={busy || retired}
            title={retired ? "Niche retired — mark worth retry first" : "Guided rebuild with learnings"}
            onClick={() => onSmartRebuild(row.id)}
          >
            {busy ? <Loader2Icon className="size-3.5 animate-spin" aria-hidden /> : <RefreshCwIcon className="size-3.5" aria-hidden />}
            Smart rebuild
          </button>
        ) : null}
        {canSmartRebuild ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
            disabled={busy || retired}
            onClick={() => onDeprioritize(row.id)}
          >
            <ArchiveIcon className="size-3.5" aria-hidden />
            Deprioritize
          </button>
        ) : null}
        {canSmartRebuild ? (
          <button
            type="button"
            className={cn("qs-btn qs-btn--ghost qs-btn--sm gap-1", retired && "text-error")}
            disabled={busy}
            onClick={() => onRetire(row.id)}
          >
            <BanIcon className="size-3.5" aria-hidden />
            {retired ? "Retired" : "Retire niche"}
          </button>
        ) : null}
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
          disabled={busy}
          onClick={() => onEval(row.id, row.title)}
        >
          <SparklesIcon className="size-3.5" aria-hidden />
          Run eval
        </button>
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
          disabled={busy}
          onClick={() => onExport(row.id)}
        >
          <DownloadIcon className="size-3.5" aria-hidden />
          GitHub pack
        </button>
        {githubPrReady && onGithubPr ? (
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm gap-1" disabled={busy} onClick={() => onGithubPr(row.id)}>
            <GitBranchIcon className="size-3.5" aria-hidden />
            PR
          </button>
        ) : null}
        {gumroadListingReady && onGumroadDraft ? (
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm gap-1" disabled={busy} onClick={() => onGumroadDraft(row.id)}>
            <StoreIcon className="size-3.5" aria-hidden />
            Gumroad
          </button>
        ) : null}
        {gumroadPublishReady && onGumroadPublish ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
            disabled={busy || row.gumroad_published === true}
            onClick={() => onGumroadPublish(row.id)}
          >
            <RocketIcon className="size-3.5" aria-hidden />
            Publish
          </button>
        ) : null}
        {row.gumroad_product_url ? (
          <a
            href={row.gumroad_product_url}
            target="_blank"
            rel="noopener noreferrer"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
          >
            <StoreIcon className="size-3.5" aria-hidden />
            Open
          </a>
        ) : null}
      </div>
    </div>
  );
}
