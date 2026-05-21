"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { usePlatform } from "@/components/hive/platform-context";
import { HIVE_IDLE_PREFETCH_ROUTES } from "@/lib/hive-route-prefetch";

/**
 * Warm route chunks during browser idle time — complements Link `prefetch` for More-sheet routes.
 * Skips routes blocked by the current platform feature matrix.
 */
export function IdleRoutePrefetcher() {
  const router = useRouter();
  const pathname = usePathname();
  const { loading, isPathAllowed } = usePlatform();

  useEffect(() => {
    if (loading) {
      return undefined;
    }

    const schedule =
      typeof window.requestIdleCallback === "function"
        ? window.requestIdleCallback.bind(window)
        : (cb: IdleRequestCallback) => window.setTimeout(() => cb({ didTimeout: false, timeRemaining: () => 0 }), 1200);

    const cancel =
      typeof window.cancelIdleCallback === "function"
        ? window.cancelIdleCallback.bind(window)
        : window.clearTimeout.bind(window);

    const handle = schedule(() => {
      for (const href of HIVE_IDLE_PREFETCH_ROUTES) {
        if (href === pathname || (href !== "/" && pathname.startsWith(`${href}/`))) {
          continue;
        }
        if (!isPathAllowed(href)) {
          continue;
        }
        try {
          void router.prefetch(href);
        } catch {
          /* prefetch is best-effort */
        }
      }
    });

    return () => cancel(handle);
  }, [loading, isPathAllowed, pathname, router]);

  return null;
}
