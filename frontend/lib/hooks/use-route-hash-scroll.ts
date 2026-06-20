"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";

const FLASH_CLASS = "qs-hash-flash";
const POLL_INTERVAL_MS = 120;
const POLL_BUDGET_MS = 3000;
const FLASH_DURATION_MS = 1600;

/**
 * Scroll to (and briefly highlight) the section identified by the URL hash.
 *
 * Mounted once in the dashboard shell so every page reacts to `#anchor` deep
 * links from operator CTAs ("Do this", cross-links, More menu). Unlike a naive
 * one-shot scroll, this polls for the target for up to 3s — async/skeleton
 * panels often mount after the route change — and adds a visible flash so the
 * operator sees that the action landed instead of perceiving "nothing happened".
 */
export function useRouteHashScroll(): void {
  const pathname = usePathname();

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    let cancelled = false;
    let pollTimer = 0;
    let flashTimer = 0;
    let flashed: HTMLElement | null = null;

    const prefersReduced =
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const clearFlash = (): void => {
      if (flashed) {
        flashed.classList.remove(FLASH_CLASS);
        flashed = null;
      }
    };

    const focusTarget = (el: HTMLElement): void => {
      el.scrollIntoView({ behavior: prefersReduced ? "auto" : "smooth", block: "start" });
      clearFlash();
      // Force reflow so the animation restarts even on repeat clicks.
      void el.offsetWidth;
      el.classList.add(FLASH_CLASS);
      flashed = el;
      window.clearTimeout(flashTimer);
      flashTimer = window.setTimeout(clearFlash, FLASH_DURATION_MS);
    };

    const start = (): void => {
      window.clearTimeout(pollTimer);
      const id = window.location.hash.replace(/^#/, "").trim();
      if (!id) {
        return;
      }
      const deadline = Date.now() + POLL_BUDGET_MS;
      const poll = (): void => {
        if (cancelled) {
          return;
        }
        const el = document.getElementById(id);
        if (el) {
          focusTarget(el);
          return;
        }
        if (Date.now() < deadline) {
          pollTimer = window.setTimeout(poll, POLL_INTERVAL_MS);
        }
      };
      poll();
    };

    start();
    window.addEventListener("hashchange", start);

    return () => {
      cancelled = true;
      window.clearTimeout(pollTimer);
      window.clearTimeout(flashTimer);
      clearFlash();
      window.removeEventListener("hashchange", start);
    };
  }, [pathname]);
}
