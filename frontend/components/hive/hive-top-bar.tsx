"use client";

/**
 * Legacy desktop top bar — intentionally disabled.
 *
 * Desktop cockpit (≥1024px) uses sidebar-only chrome. Mobile/tablet use
 * `HiveMobileHeader` + bottom nav. Do not remount this component without
 * explicit product sign-off.
 */

export interface HiveTopBarProps {
  email: string;
  displayName?: string | null;
}

/** @deprecated Returns null — not used in shell. */
export function HiveTopBar(_props: HiveTopBarProps): null {
  return null;
}
