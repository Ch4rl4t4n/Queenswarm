"use client";

import { useEffect } from "react";

/** Scroll to a section id when the URL hash changes (e.g. /agents#hierarchy). */
export function useRouteHashScroll(): void {
  useEffect(() => {
    const scrollToHash = (): void => {
      const id = window.location.hash.replace(/^#/, "").trim();
      if (!id) {
        return;
      }
      const target = document.getElementById(id);
      if (target) {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    };

    scrollToHash();
    window.addEventListener("hashchange", scrollToHash);
    return () => window.removeEventListener("hashchange", scrollToHash);
  }, []);
}
