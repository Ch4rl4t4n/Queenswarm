"use client";

import Link from "next/link";
import { Sparkles } from "lucide-react";

import { usePlatform } from "@/components/hive/platform-context";
import { cn } from "@/lib/utils";

interface ProUpgradeBannerProps {
  className?: string;
  /** Short reason shown beside the CTA. */
  reason?: string;
}

/** Commercial Free tier upsell — links to billing settings. */
export function ProUpgradeBanner({ className, reason }: ProUpgradeBannerProps): JSX.Element | null {
  const { platformMode, subscriptionTier, loading, soloMode, hasFeature } = usePlatform();

  if (loading || soloMode || !hasFeature("billing_settings")) {
    return null;
  }
  if (platformMode !== "commercial" || subscriptionTier !== "free") {
    return null;
  }

  return (
    <div
      className={cn(
        "flex flex-wrap items-center justify-between gap-3 rounded-xl border border-pollen/35 bg-pollen/[0.08] px-4 py-3",
        className,
      )}
    >
      <div className="flex min-w-0 items-start gap-2">
        <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-pollen" aria-hidden />
        <div className="min-w-0">
          <p className="text-sm font-medium text-(--qs-text)">Upgrade to Pro</p>
          <p className="text-xs text-(--qs-text-3)">
            {reason ?? "Unlimited agents & swarms, voice Ballroom, recipes, and advanced memory."}
          </p>
        </div>
      </div>
      <Link href="/settings/billing" className="qs-btn qs-btn--primary qs-btn--sm shrink-0">
        Upgrade on billing
      </Link>
    </div>
  );
}
