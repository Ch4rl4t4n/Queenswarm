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

    // Reload once when a newly deployed worker takes control so the shell never
    // gets stuck on a stale cached build (guarded against reload loops).
    let reloading = false;
    const onControllerChange = (): void => {
      if (reloading) {
        return;
      }
      reloading = true;
      window.location.reload();
    };
    navigator.serviceWorker.addEventListener("controllerchange", onControllerChange);

    void navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .then((registration) => {
        // Force an update check on every load so version bumps activate promptly.
        void registration.update().catch(() => undefined);
      })
      .catch(() => {
        /* registration optional — never block UI */
      });

    return () => {
      navigator.serviceWorker.removeEventListener("controllerchange", onControllerChange);
    };
  }, []);

  return null;
}
