"use client";

import Link from "next/link";
import { Sparkles } from "lucide-react";

import { V4Badge, V4Card } from "@/components/ui/v4";

/** Compact hero CTA — unified Swarm Builder entry (Phase 0 week 2). */
export function SwarmBuilderEntryCard(): JSX.Element {
  return (
    <V4Card className="v4-card-interactive border-pollen/25 bg-linear-to-r from-pollen/10 via-transparent to-cyan/5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Sparkles className="h-4 w-4 text-pollen" aria-hidden />
            <p className="text-sm font-semibold text-(--qs-text)">Swarm Builder</p>
            <V4Badge tone="ok">~10 min</V4Badge>
          </div>
          <p className="mt-1 text-xs text-(--qs-text-3)">
            Exec Assistant ships with 4 agentic patterns — planning, RAG, reflection, and goal monitoring. Zero prompt
            engineering.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Link href="/swarms/new?template=exec-assistant" className="qs-btn qs-btn--ghost qs-btn--sm">
            Open Exec Assistant
          </Link>
          <Link href="/swarms/new?template=lead-waterfall" className="qs-btn qs-btn--ghost qs-btn--sm">
            Lead Waterfall
          </Link>
          <Link href="/swarms/new?template=content-flywheel" className="qs-btn qs-btn--ghost qs-btn--sm">
            Content Flywheel
          </Link>
          <Link href="/swarms/new?template=product-ship" className="qs-btn qs-btn--ghost qs-btn--sm">
            Product Ship
          </Link>
          <Link href="/swarms/new" className="qs-btn qs-btn--ghost qs-btn--sm">
            All templates
          </Link>
        </div>
      </div>
    </V4Card>
  );
}
