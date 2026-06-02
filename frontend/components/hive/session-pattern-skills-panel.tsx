"use client";

import type { JSX } from "react";

import Link from "next/link";
import { ChevronDown, Sparkles } from "lucide-react";
import { useState } from "react";

import { agenticPatternLabel } from "@/lib/agentic-pattern-labels";
import { MANUAL_HREFS } from "@/lib/manual-routes";
import type { SessionPatternSkillsSnapshot } from "@/lib/session-pattern-skills";
import { V4Badge } from "@/components/ui/v4";
import { cn } from "@/lib/utils";

interface SessionPatternSkillsPanelProps {
  snapshot: SessionPatternSkillsSnapshot;
  variant?: "compact" | "full" | "preview";
  className?: string;
}

function PatternBadge({ patternId, tone }: { patternId: string; tone: "gold" | "info" }): JSX.Element {
  return (
    <V4Badge tone={tone} className="max-w-full truncate">
      {agenticPatternLabel(patternId)}
    </V4Badge>
  );
}

function SkillBadge({ slug }: { slug: string }): JSX.Element {
  return (
    <span className="inline-flex max-w-full items-center rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-(family-name:--font-jetbrains-mono) text-[10px] text-emerald-200">
      {slug}
    </span>
  );
}

/** Operator-facing Pattern Router + skill selection for one supervisor session. */
export function SessionPatternSkillsPanel({
  snapshot,
  variant = "compact",
  className,
}: SessionPatternSkillsPanelProps): JSX.Element | null {
  const [rationaleOpen, setRationaleOpen] = useState(variant === "full");

  if (!snapshot.routerEnabled || !snapshot.patterns) {
    if (variant === "preview") {
      return (
        <p className={cn("text-xs text-(--qs-text-4)", className)}>
          Pattern Router disabled — enable in Settings → Harness.
        </p>
      );
    }
    return null;
  }

  const { patterns, allSkills, suggestedSkills, skillsByRole } = snapshot;
  const primaryLimit = variant === "compact" ? 4 : patterns.primary.length;
  const secondaryLimit = variant === "compact" ? 2 : patterns.secondary.length;
  const skillLimit = variant === "compact" ? 6 : allSkills.length || suggestedSkills.length;

  const displaySkills =
    allSkills.length > 0 ? allSkills : variant === "preview" ? suggestedSkills : allSkills;

  const routerLabel =
    patterns.router_version.includes("llm") ? "LLM-refined" : patterns.router_version || "heuristic";

  return (
    <div
      className={cn(
        variant === "full"
          ? "qs-bubble-inner space-y-3 p-3"
          : variant === "preview"
            ? "rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-3 py-2.5"
            : "mt-2 space-y-1.5",
        className,
      )}
      data-testid="session-pattern-skills-panel"
    >
      <div className="flex flex-wrap items-center gap-2">
        {variant !== "compact" ? (
          <Sparkles className="h-3.5 w-3.5 shrink-0 text-cyan-300" aria-hidden />
        ) : null}
        <p
          className={cn(
            "font-semibold uppercase tracking-wider text-(--qs-text-3)",
            variant === "compact" ? "text-[10px]" : "text-[11px]",
          )}
        >
          Pattern Router
        </p>
        <V4Badge tone="info">{routerLabel}</V4Badge>
        {patterns.forced_reflection ? <V4Badge tone="gold">reflection gate</V4Badge> : null}
        {patterns.resource_aware ? <V4Badge tone="warn">resource-aware</V4Badge> : null}
        {variant !== "compact" ? (
          <Link href={MANUAL_HREFS.manualPatternRouter} className="ml-auto text-[10px] text-cyan-300 hover:underline">
            Manual →
          </Link>
        ) : null}
      </div>

      {patterns.primary.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {patterns.primary.slice(0, primaryLimit).map((pid) => (
            <PatternBadge key={`p-${pid}`} patternId={pid} tone="gold" />
          ))}
          {variant === "compact" && patterns.primary.length > primaryLimit ? (
            <V4Badge tone="info">+{patterns.primary.length - primaryLimit}</V4Badge>
          ) : null}
        </div>
      ) : null}

      {variant !== "compact" && patterns.secondary.length > 0 ? (
        <div className="space-y-1">
          <p className="text-[10px] font-medium uppercase tracking-wider text-(--qs-text-4)">Secondary</p>
          <div className="flex flex-wrap gap-1.5">
            {patterns.secondary.slice(0, secondaryLimit).map((pid) => (
              <PatternBadge key={`s-${pid}`} patternId={pid} tone="info" />
            ))}
          </div>
        </div>
      ) : null}

      {displaySkills.length > 0 ? (
        <div className="space-y-1">
          <p className="text-[10px] font-medium uppercase tracking-wider text-(--qs-text-4)">
            {variant === "preview" ? "Suggested skills" : "Resolved skills"}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {displaySkills.slice(0, skillLimit).map((slug) => (
              <SkillBadge key={slug} slug={slug} />
            ))}
            {displaySkills.length > skillLimit ? (
              <span className="text-[10px] text-(--qs-text-4)">+{displaySkills.length - skillLimit}</span>
            ) : null}
          </div>
        </div>
      ) : null}

      {variant === "full" && Object.keys(skillsByRole).length > 0 ? (
        <div className="space-y-2 border-t border-(--qs-border) pt-2">
          <p className="text-[10px] font-medium uppercase tracking-wider text-(--qs-text-4)">Skills by role</p>
          {Object.entries(skillsByRole).map(([role, skills]) => (
            <div key={role} className="space-y-1">
              <p className="font-(family-name:--font-jetbrains-mono) text-[10px] text-(--qs-text-3)">{role}</p>
              <div className="flex flex-wrap gap-1">
                {skills.map((slug) => (
                  <SkillBadge key={`${role}-${slug}`} slug={slug} />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {patterns.rationale.length > 0 && variant !== "compact" ? (
        <div className="border-t border-(--qs-border) pt-2">
          <button
            type="button"
            className="flex w-full items-center gap-1 text-left text-[10px] font-semibold uppercase tracking-wider text-(--qs-text-3) hover:text-(--qs-text-2)"
            onClick={() => setRationaleOpen((open) => !open)}
          >
            <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", rationaleOpen && "rotate-180")} aria-hidden />
            Why these patterns
          </button>
          {rationaleOpen ? (
            <ul className="mt-2 list-disc space-y-1 pl-4 text-xs leading-relaxed text-(--qs-text-3)">
              {patterns.rationale.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {variant === "preview" ? (
        <p className="text-[10px] text-(--qs-text-4)">
          Preview only — final selection is saved on Create session.{" "}
          <Link href={MANUAL_HREFS.settingsHarness} className="text-cyan-300 hover:underline">
            Harness Pattern Explorer
          </Link>
        </p>
      ) : null}
    </div>
  );
}
