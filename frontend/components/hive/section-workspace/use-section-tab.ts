"use client";

import { useCallback } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

export interface UseSectionTabOptions<T extends string> {
  /** Allowed sub-section ids. */
  tabs: readonly T[];
  /** Default sub-section when no query param is present. */
  defaultTab: T;
  /** Query param name (default `tab`). */
  param?: string;
}

/**
 * Sub-section state synced to a URL query param without a route change.
 *
 * Switching a sub-section updates `?tab=` via `router.replace({ scroll: false })`
 * so the operator stays inside the same section (no jumping between sections).
 */
export function useSectionTab<T extends string>({
  tabs,
  defaultTab,
  param = "tab",
}: UseSectionTabOptions<T>): readonly [T, (next: T) => void] {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const raw = searchParams.get(param);
  const active = (raw && (tabs as readonly string[]).includes(raw) ? raw : defaultTab) as T;

  const setActive = useCallback(
    (next: T) => {
      const params = new URLSearchParams(searchParams.toString());
      if (next === defaultTab) {
        params.delete(param);
      } else {
        params.set(param, next);
      }
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [router, pathname, searchParams, defaultTab, param],
  );

  return [active, setActive] as const;
}
