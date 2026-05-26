"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { usePlatform } from "@/components/hive/platform-context";
import { useCenterActiveInScrollRow } from "@/lib/hooks/use-center-active-in-scroll-row";
import { filterSettingsNavSections } from "@/lib/settings-nav";
import { isSettingsNavSectionActive } from "@/lib/settings-panel-registry";
import { useRoutePrefetch } from "@/lib/use-route-prefetch";
import { cn } from "@/lib/utils";

export function SettingsSubnav() {
  const pathname = usePathname();
  const prefetchRoute = useRoutePrefetch();
  const { features, isAdmin, platformMode } = usePlatform();
  const sections = filterSettingsNavSections(features, { isAdmin, platformMode });
  const scrollRef = useCenterActiveInScrollRow<HTMLElement>(pathname);

  return (
    <nav ref={scrollRef} aria-label="Settings sections" className="v4-subtab-row w-full max-w-full">
      {sections.map(({ href, label, icon: Icon }) => {
        const active = isSettingsNavSectionActive(pathname, href);
        return (
          <Link
            key={href}
            href={href}
            prefetch
            className={cn("v4-subtab", active && "v4-subtab--active")}
            onMouseEnter={() => prefetchRoute(href)}
            onFocus={() => prefetchRoute(href)}
          >
            <Icon className="h-3.5 w-3.5" aria-hidden />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
