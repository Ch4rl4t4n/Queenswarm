"use client";

import Link from "next/link";

import { usePlatform } from "@/components/hive/platform-context";
import { resolveTenantBranding } from "@/lib/tenant-branding";
import { hiveOverviewHref } from "@/lib/hive-home-route";
import { cn } from "@/lib/utils";

interface HiveBrandMarkProps {
  readonly onNavigate?: () => void;
  readonly compact?: boolean;
  /** Hide tagline row — mobile sticky header shows brand name only. */
  readonly showTagline?: boolean;
  readonly className?: string;
}

/** Sidebar / mobile hive brand — respects tenant white-label when configured. */
export function HiveBrandMark({
  onNavigate,
  compact = false,
  showTagline = true,
  className,
}: HiveBrandMarkProps): JSX.Element {
  const { tenantBranding, soloMode } = usePlatform();
  const brand = resolveTenantBranding(tenantBranding);

  return (
    <Link
      href={hiveOverviewHref({ soloMode })}
      aria-label={`${brand.brand_name} home`}
      className={cn(
        "flex w-full min-w-0 flex-col items-center justify-center text-center touch-manipulation",
        compact ? "px-2" : "px-10",
        className,
      )}
      prefetch
      onClick={() => onNavigate?.()}
    >
      <div className="flex max-w-full items-center justify-center gap-2">
        {brand.logo_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={brand.logo_url} alt="" className="h-7 w-7 shrink-0 rounded-md object-contain" />
        ) : null}
        <span
          className={cn(
            "truncate font-[family-name:var(--font-poppins)] font-bold tracking-tight text-(--qs-text)",
            compact ? "text-sm" : "text-[17px]",
          )}
          style={brand.accent_hex ? { color: brand.accent_hex } : undefined}
        >
          {brand.brand_name}
        </span>
      </div>
      {showTagline ? (
        <span className="mt-0.5 block truncate text-[10px] font-medium uppercase tracking-[0.18em] text-(--qs-text-3)">
          {brand.tagline}
        </span>
      ) : null}
    </Link>
  );
}
