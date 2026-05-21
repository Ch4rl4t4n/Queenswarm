"use client";

import { useEffect } from "react";

import { refreshDashboardSession } from "@/lib/hive-bearer-token";

const REFRESH_INTERVAL_MS = 10 * 60 * 1000;
const VISIBILITY_REFRESH_DEBOUNCE_MS = 4_000;

/** Silently rotate the dashboard access JWT while a refresh cookie remains valid. */
export function useDashboardSessionRefresh(): void {
  useEffect(() => {
    const interval = window.setInterval(() => {
      void refreshDashboardSession();
    }, REFRESH_INTERVAL_MS);

    let visibilityTimer: number | undefined;

    const onVisible = (): void => {
      if (document.visibilityState !== "visible") {
        return;
      }
      if (visibilityTimer !== undefined) {
        window.clearTimeout(visibilityTimer);
      }
      visibilityTimer = window.setTimeout(() => {
        void refreshDashboardSession();
      }, VISIBILITY_REFRESH_DEBOUNCE_MS);
    };

    window.addEventListener("focus", onVisible);
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      window.clearInterval(interval);
      if (visibilityTimer !== undefined) {
        window.clearTimeout(visibilityTimer);
      }
      window.removeEventListener("focus", onVisible);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);
}
