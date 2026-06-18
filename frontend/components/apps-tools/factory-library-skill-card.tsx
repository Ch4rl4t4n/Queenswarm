"use client";

import {
  ArchiveIcon,
  BanIcon,
  DownloadIcon,
  ExternalLinkIcon,
  GitBranchIcon,
  Loader2Icon,
  RefreshCwIcon,
  RocketIcon,
  SparklesIcon,
  StoreIcon,
  Trash2Icon,
} from "lucide-react";

import { ForagerProgressCell } from "@/components/hive/forager-progress-cell";
import { V4Badge, type V4BadgeTone } from "@/components/ui/v4";
import { LIBRARY_SIEVE_LABELS, sellableIssueLabel, verdictTone } from "@/lib/sellable-issue-labels";
import { cn } from "@/lib/utils";

export interface InlineEvalResult {
  passed: boolean;
  tier: string;
  score: number;
  issues: string[];
  evaluated_at: string;
}

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
  library_verdict: string | null;
  library_verdict_reason: string | null;
  library_verdict_action: string | null;
  purge_eligible?: boolean;
}

function shortSkillId(id: string): string {
  return `S-${id.replace(/-/g, "").slice(0, 4).toUpperCase()}`;
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

function dispositionTone(disposition: string | null): V4BadgeTone {
  if (disposition === "worth_retry") return "ok";
  if (disposition === "deprioritized") return "warn";
  if (disposition === "retired") return "err";
  return "info";
}

function tierTone(tier: string): V4BadgeTone {
  if (tier === "sellable") return "ok";
  if (tier === "draft") return "info";
  return "warn";
}

function verdictLabel(verdict: string | null): string {
  if (!verdict) return "pending";
  return LIBRARY_SIEVE_LABELS[verdict as keyof typeof LIBRARY_SIEVE_LABELS] ?? verdict.replaceAll("_", " ");
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
  onRemove: (id: string, title: string) => void;
  onEval: (id: string, title: string) => void;
  onExport?: (id: string) => void;
  onGithubPr?: (id: string) => void;
  onGumroadDraft?: (id: string) => void;
  onGumroadPublish?: (id: string) => void;
  inlineEval?: InlineEvalResult | null;
  rebuildQueued?: boolean;
  onDownloadEvalReport?: (id: string, title: string) => void;
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
  onRemove,
  onEval,
  onExport,
  onGithubPr,
  onGumroadDraft,
  onGumroadPublish,
  inlineEval,
  rebuildQueued,
  onDownloadEvalReport,
}: FactoryLibrarySkillCardProps): JSX.Element {
  const busy = busyId === row.id;
  const rejected = row.sellable_tier === "rejected";
  const draft = row.sellable_tier === "draft";
  const canSmartRebuild = rejected || draft;
  const retired = row.factory_disposition === "retired";
  const dispLabel = dispositionLabel(row.factory_disposition);
  const verdict = row.library_verdict;
  const issueLabels = row.sellable_issues.map(sellableIssueLabel);
  const scorePercent = Math.round(row.sellable_score * 100);
  const progressDetail = row.library_verdict_reason ?? row.description;

  return (
    <div
      className={cn(
        "v4-session-row",
        verdict === "launch" && "border-success/30",
        verdict === "retire" && "border-error/35",
      )}
      data-testid="factory-library-row"
      data-library-verdict={verdict ?? "unknown"}
    >
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex flex-wrap items-center gap-2">
          <span className="font-(family-name:--font-jetbrains-mono) text-[11px] text-(--qs-text-3)">
            {shortSkillId(row.id)}
          </span>
          {verdict ? <V4Badge tone={verdictTone(verdict)}>{verdictLabel(verdict)}</V4Badge> : null}
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
          {rebuildQueued ? <V4Badge tone="info">rebuild queued</V4Badge> : null}
          {inlineEval ? (
            <V4Badge tone={inlineEval.passed ? "ok" : "err"}>
              eval {inlineEval.passed ? "pass" : "fail"}
            </V4Badge>
          ) : null}
        </div>

        <p className="v4-session-goal text-sm font-medium text-(--qs-text)" title={row.title}>
          {row.title}
        </p>
        <p className="mt-1 line-clamp-2 text-xs text-(--qs-text-3)">
          {progressDetail || "Tenant harness skill from Skill Factory — export when sellable."}
        </p>
        <p className="mt-1 font-(family-name:--font-jetbrains-mono) text-[10px] text-pollen">{row.slug}</p>

        <div className="mt-2 space-y-1.5" data-testid="factory-library-pattern-meta">
          {row.library_verdict_action ? (
            <p className="text-[11px] text-(--qs-text-4)">→ {row.library_verdict_action}</p>
          ) : null}

          {issueLabels.length > 0 ? (
            <div className="space-y-1">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-text-3)">
                Sellable signals
              </p>
              <div className="flex flex-wrap gap-1.5">
                {issueLabels.slice(0, 6).map((label) => (
                  <V4Badge key={`${row.id}-${label}`} tone="info">
                    {label}
                  </V4Badge>
                ))}
              </div>
            </div>
          ) : null}

          {row.gumroad_product_id ? (
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-text-3)">
                Launch channel
              </p>
              <V4Badge tone={row.gumroad_published ? "ok" : "gold"}>
                {row.gumroad_published ? "gumroad live" : "gumroad draft"}
              </V4Badge>
            </div>
          ) : null}

          <ForagerProgressCell
            pct={scorePercent}
            detail={`Sellable score ${scorePercent}% · ${row.sellable_tier}`}
          />

          {inlineEval && inlineEval.issues.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {inlineEval.issues.slice(0, 4).map((issue) => (
                <V4Badge key={`${row.id}-eval-${issue}`} tone={inlineEval.passed ? "ok" : "err"}>
                  {sellableIssueLabel(issue)}
                </V4Badge>
              ))}
              {onDownloadEvalReport ? (
                <button
                  type="button"
                  className="text-[10px] text-cyan underline"
                  onClick={() => onDownloadEvalReport(row.id, row.title)}
                >
                  Eval report
                </button>
              ) : null}
            </div>
          ) : null}

          {row.factory_disposition_note ? (
            <p className="text-[11px] text-(--qs-text-4)">Note: {row.factory_disposition_note}</p>
          ) : null}
        </div>
      </div>

      <div className="flex shrink-0 flex-wrap items-center gap-2">
        <span className="text-xs text-(--qs-text-3)">
          {scorePct(row.sellable_score)} · {row.sellable_tier}
        </span>

        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
          disabled={busy}
          onClick={() => onEval(row.id, row.title)}
        >
          {busy ? <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <SparklesIcon className="h-3.5 w-3.5" aria-hidden />}
          {inlineEval ? "Re-eval" : "Eval"}
        </button>

        {onExport ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
            disabled={busy}
            onClick={() => onExport(row.id)}
          >
            <DownloadIcon className="h-3.5 w-3.5" aria-hidden />
            Pack
          </button>
        ) : null}

        {canSmartRebuild ? (
          <button
            type="button"
            className={cn(
              "qs-btn qs-btn--sm gap-1.5",
              rejected ? "qs-btn--primary" : "qs-btn--ghost",
            )}
            disabled={busy || retired}
            title={retired ? "Niche retired — mark worth retry first" : "Guided rebuild with learnings"}
            onClick={() => onSmartRebuild(row.id)}
          >
            <RefreshCwIcon className="h-3.5 w-3.5" aria-hidden />
            Rebuild
          </button>
        ) : null}

        {githubPrReady && onGithubPr ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
            disabled={busy}
            onClick={() => onGithubPr(row.id)}
          >
            <GitBranchIcon className="h-3.5 w-3.5" aria-hidden />
            PR
          </button>
        ) : null}

        {gumroadListingReady && onGumroadDraft ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
            disabled={busy}
            onClick={() => onGumroadDraft(row.id)}
          >
            <StoreIcon className="h-3.5 w-3.5" aria-hidden />
            Gumroad
          </button>
        ) : null}

        {gumroadPublishReady && onGumroadPublish && row.gumroad_product_id ? (
          <button
            type="button"
            className="qs-btn qs-btn--green qs-btn--sm gap-1.5"
            disabled={busy || row.gumroad_published === true}
            onClick={() => onGumroadPublish(row.id)}
          >
            <RocketIcon className="h-3.5 w-3.5" aria-hidden />
            Publish
          </button>
        ) : null}

        {row.gumroad_product_url ? (
          <a
            href={row.gumroad_product_url}
            target="_blank"
            rel="noopener noreferrer"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
          >
            <ExternalLinkIcon className="h-3.5 w-3.5" aria-hidden />
            Open
          </a>
        ) : null}

        {canSmartRebuild ? (
          <>
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
              disabled={busy || retired}
              onClick={() => onDeprioritize(row.id)}
            >
              <ArchiveIcon className="h-3.5 w-3.5" aria-hidden />
              Deprioritize
            </button>
            <button
              type="button"
              className={cn("qs-btn qs-btn--ghost qs-btn--sm gap-1.5", retired && "text-error")}
              disabled={busy}
              onClick={() => onRetire(row.id)}
            >
              <BanIcon className="h-3.5 w-3.5" aria-hidden />
              {retired ? "Retired" : "Retire"}
            </button>
          </>
        ) : null}

        {row.purge_eligible ? (
          <button
            type="button"
            className={cn("qs-btn qs-btn--danger qs-btn--sm gap-1.5", busy && "opacity-60")}
            disabled={busy}
            title="Remove from library — reviewed, no launch value"
            onClick={() => onRemove(row.id, row.title)}
          >
            <Trash2Icon className="h-3.5 w-3.5" aria-hidden />
            Delete
          </button>
        ) : null}
      </div>
    </div>
  );
}
