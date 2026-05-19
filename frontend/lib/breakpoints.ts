/**
 * Single source of truth for Queenswarm responsive breakpoints.
 * Aligns with Tailwind defaults: md = 768px, lg = 1024px.
 */

/** Inclusive max width for phone layouts. */
export const MOBILE_MAX_PX = 767;

/** Inclusive min width for tablet layouts. */
export const TABLET_MIN_PX = 768;

/** Inclusive max width for tablet layouts (below desktop sidebar). */
export const TABLET_MAX_PX = 1023;

/** Inclusive min width for desktop persistent sidebar (no top bar). */
export const DESKTOP_MIN_PX = 1024;

export const BREAKPOINTS = {
  mobileMax: MOBILE_MAX_PX,
  tabletMin: TABLET_MIN_PX,
  tabletMax: TABLET_MAX_PX,
  desktopMin: DESKTOP_MIN_PX,
} as const;

/** Use with `window.matchMedia` / `useMediaQuery`. */
export const MEDIA_QUERIES = {
  mobile: `(max-width: ${MOBILE_MAX_PX}px)`,
  tablet: `(min-width: ${TABLET_MIN_PX}px) and (max-width: ${TABLET_MAX_PX}px)`,
  desktop: `(min-width: ${DESKTOP_MIN_PX}px)`,
  belowDesktop: `(max-width: ${TABLET_MAX_PX}px)`,
  tabletUp: `(min-width: ${TABLET_MIN_PX}px)`,
} as const;

export type ViewportTier = "mobile" | "tablet" | "desktop";

/** Map viewport width to layout tier. */
export function viewportTierFromWidth(widthPx: number): ViewportTier {
  if (widthPx <= MOBILE_MAX_PX) {
    return "mobile";
  }
  if (widthPx <= TABLET_MAX_PX) {
    return "tablet";
  }
  return "desktop";
}
