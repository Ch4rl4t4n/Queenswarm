"use client";

import { useRouter } from "next/navigation";
import { useCallback, useRef } from "react";

/** Warm a route chunk on pointer hover — complements Link `prefetch`. */
export function useRoutePrefetch() {
  const router = useRouter();
  const warmed = useRef<Set<string>>(new Set());

  return useCallback(
    (href: string) => {
      if (!href || warmed.current.has(href)) {
        return;
      }
      warmed.current.add(href);
      try {
        void router.prefetch(href);
      } catch {
        /* best-effort */
      }
    },
    [router],
  );
}
