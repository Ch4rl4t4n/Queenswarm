"use client";

import { Layers, Loader2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { V4Badge, V4Card } from "@/components/ui/v4";
import { hiveGet } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface Tier0SectionState {
  section_id: string;
  label: string;
  char_count: number;
  estimated_tokens: number;
  preview: string;
  filled: boolean;
}

export interface InjectionTierState {
  tier_id: string;
  label: string;
  order: number;
  char_count: number;
  estimated_tokens: number;
  active: boolean;
  inject_timing: string;
  preview: string;
  sections: Tier0SectionState[];
}

export interface Tier0InjectionStripState {
  enabled: boolean;
  visible: boolean;
  frozen_snapshot_label: string;
  tiers: InjectionTierState[];
  recall_mode: string;
  deep_recall_budget_chars: number;
  chroma_enabled: boolean;
  operator_hint: string;
  edit_href: string;
}

interface Tier0InjectionStripPanelProps {
  variant?: "full" | "compact";
  className?: string;
  refreshKey?: number | string;
}

function tierTone(tierId: string, active: boolean): string {
  if (!active) {
    return "border-(--qs-border) bg-black/15 opacity-60";
  }
  if (tierId === "tier0") {
    return "border-purple-500/35 bg-purple-500/10";
  }
  if (tierId === "tier1") {
    return "border-cyan/30 bg-cyan/5";
  }
  return "border-pollen/30 bg-pollen/5";
}

/** MEM3 — Tier-0 Brain Pack injection strip before deep Chroma recall. */
export function Tier0InjectionStripPanel({
  variant = "full",
  className,
  refreshKey,
}: Tier0InjectionStripPanelProps): JSX.Element | null {
  const [state, setState] = useState<Tier0InjectionStripState | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await hiveGet<Tier0InjectionStripState>("memory/curated/tier0-injection-strip");
      setState(data);
    } catch {
      setState(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  if (loading) {
    return (
      <div className={cn("flex items-center gap-2 text-xs text-(--qs-text-3)", className)}>
        <Loader2 className="size-3 animate-spin" aria-hidden />
        Loading injection tiers…
      </div>
    );
  }

  if (!state?.enabled || !state.visible) {
    return null;
  }

  if (variant === "compact") {
    const tier0 = state.tiers.find((tier) => tier.tier_id === "tier0");
    return (
      <div
        className={cn("rounded-lg border border-purple-500/30 bg-purple-500/10 px-3 py-2 text-xs", className)}
        data-testid="tier0-injection-strip-compact"
      >
        <span className="font-mono text-purple-200">
          Tier-0 ~{tier0?.estimated_tokens ?? 0} tok · deep recall budget {state.deep_recall_budget_chars} chars
        </span>
      </div>
    );
  }

  return (
    <V4Card
      className={cn("border-purple-500/25 p-3", className)}
      id="tier0-injection-strip"
      data-testid="tier0-injection-strip-panel"
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Layers className="size-4 text-purple-300" aria-hidden />
        <span className="text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">Injection ladder</span>
        <V4Badge tone="purple">MEM3</V4Badge>
        <V4Badge tone="info">{state.frozen_snapshot_label}</V4Badge>
      </div>

      <p className="mb-3 text-xs text-(--qs-text-3)">{state.operator_hint}</p>

      <ol className="space-y-3">
        {state.tiers.map((tier) => (
          <li
            key={tier.tier_id}
            className={cn("rounded-lg border px-3 py-2.5", tierTone(tier.tier_id, tier.active))}
            data-testid={`injection-tier-${tier.tier_id}`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <V4Badge tone={tier.active ? "purple" : "info"}>{tier.label}</V4Badge>
                {!tier.active ? <V4Badge tone="info">inactive</V4Badge> : null}
              </div>
              <span className="font-mono text-[11px] text-cyan">
                {tier.char_count} chars · ~{tier.estimated_tokens} tok
              </span>
            </div>
            <p className="mt-1 text-[10px] uppercase tracking-wide text-(--qs-text-4)">{tier.inject_timing}</p>
            <p className="mt-1.5 text-xs text-(--qs-text-2)">{tier.preview}</p>

            {tier.tier_id === "tier0" && tier.sections.length > 0 ? (
              <ul className="mt-2 grid gap-1.5 sm:grid-cols-2">
                {tier.sections.map((section) => (
                  <li
                    key={section.section_id}
                    className={cn(
                      "rounded-md border px-2 py-1.5 text-[11px]",
                      section.filled ? "border-cyan/20 bg-black/20" : "border-(--qs-border) opacity-70",
                    )}
                  >
                    <span className="font-semibold text-(--qs-text-2)">{section.label}</span>
                    <span className="ml-2 font-mono text-(--qs-text-4)">
                      {section.char_count}c · ~{section.estimated_tokens}t
                    </span>
                    <p className="mt-0.5 text-(--qs-text-3)">{section.preview}</p>
                  </li>
                ))}
              </ul>
            ) : null}
          </li>
        ))}
      </ol>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-(--qs-text-3)">
        <V4Badge tone="info">recall {state.recall_mode}</V4Badge>
        <V4Badge tone="gold">deep budget {state.deep_recall_budget_chars}</V4Badge>
        {state.chroma_enabled ? <V4Badge tone="ok">Chroma on</V4Badge> : <V4Badge tone="warn">Chroma off</V4Badge>}
        <Link href={state.edit_href} className="text-cyan hover:underline">
          Edit Brain Pack
        </Link>
      </div>
    </V4Card>
  );
}
