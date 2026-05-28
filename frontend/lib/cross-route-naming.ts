/**
 * Whole-App UI Reorder — cross-route naming + canonical operator paths (Phase 5).
 */

/** User-facing product name for the operator control plane home. */
export const AGENTIC_OS_PRODUCT_NAME = "Agentic OS";

/** Canonical browser path for Agentic OS (legacy /cockpit redirects here). */
export const AGENTIC_OS_CANONICAL_PATH = "/agentic-os";

/** Paths that should resolve to the same operator home chrome. */
export const AGENTIC_OS_ROUTE_ALIASES: readonly string[] = [
  "/agentic-os",
  "/cockpit",
  "/",
];

export function isAgenticOsRoute(pathname: string): boolean {
  const normalized = pathname.replace(/\/$/, "") || "/";
  return AGENTIC_OS_ROUTE_ALIASES.includes(normalized);
}
