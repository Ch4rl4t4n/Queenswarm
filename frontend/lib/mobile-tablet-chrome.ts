/**
 * Whole-App UI Reorder — mobile/tablet chrome helpers (Phase 6).
 * Sticky header titles align with `hive-mobile-meta.ts` route labels.
 */

import { hiveMobileRouteMeta } from "@/lib/hive-mobile-meta";

export interface MobileChromeTitle {
  kicker: string;
  title: string;
}

/** Resolve sticky mobile header kicker + title for a pathname. */
export function mobileChromeTitleForPath(pathname: string): MobileChromeTitle {
  const meta = hiveMobileRouteMeta(pathname);
  return {
    kicker: meta.kicker,
    title: meta.pageTitleSuffix ?? meta.kicker,
  };
}
