"use client";

import { useEffect } from "react";

import { OPERATOR_CONTROL_PLANE_ENABLED } from "@/lib/feature-flags";
import { warmAllSettingsPanelChunks } from "@/lib/settings-panel-registry";

/** Warm heavy page-client chunks during idle — pairs with IdleRoutePrefetcher. */
const HOT_CLIENT_CHUNKS: Array<() => Promise<unknown>> = [
  () => import("@/components/hive/colony-console"),
  () => import("@/components/hive/agents-page-client"),
  () => import("@/components/hive/tasks-page-client"),
  () => import("@/components/hive/knowledge-page-client"),
  () => import("@/components/hive/swarms-page-client"),
  () => import("@/components/hive/integrations-page-client"),
  () => import("@/components/hive/ballroom-page-client"),
  () => import("@/components/hive/workflows-dag-page"),
  ...(OPERATOR_CONTROL_PLANE_ENABLED
    ? [() => import("@/components/hive/operator-cockpit-panel")]
    : []),
  // costs-cockpit-page is an async Server Component (hive-server) — warm via route prefetch only
];

export function HotRouteChunkWarmer() {
  useEffect(() => {
    const schedule =
      typeof window.requestIdleCallback === "function"
        ? window.requestIdleCallback.bind(window)
        : (cb: IdleRequestCallback) => window.setTimeout(() => cb({ didTimeout: false, timeRemaining: () => 0 }), 1500);

    const cancel =
      typeof window.cancelIdleCallback === "function"
        ? window.cancelIdleCallback.bind(window)
        : window.clearTimeout.bind(window);

    const handle = schedule(() => {
      for (const load of HOT_CLIENT_CHUNKS) {
        void load();
      }
      warmAllSettingsPanelChunks();
    });

    return () => cancel(handle);
  }, []);

  return null;
}
