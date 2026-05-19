"use client";

import { useEffect } from "react";

import { MEDIA_QUERIES } from "@/lib/breakpoints";

/** Register shell service worker on mobile/tablet only (production or explicit flag). */
export function HiveServiceWorker(): null {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) {
      return undefined;
    }

    const enabled =
      process.env.NODE_ENV === "production" ||
      process.env.NEXT_PUBLIC_PWA_SHELL === "1";

    if (!enabled) {
      return undefined;
    }

    const mq = window.matchMedia(MEDIA_QUERIES.belowDesktop);
    if (!mq.matches) {
      return undefined;
    }

    void navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {
      /* registration optional — never block UI */
    });

    return undefined;
  }, []);

  return null;
}
