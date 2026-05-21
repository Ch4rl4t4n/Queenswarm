"use client";

import { useEffect, useRef } from "react";

/**
 * Keeps the active pill in a horizontal subtab row scrolled to the viewport center.
 */
export function useCenterActiveInScrollRow<T extends HTMLElement = HTMLDivElement>(activeKey: string) {
  const containerRef = useRef<T>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return undefined;
    }

    const frame = requestAnimationFrame(() => {
      const active =
        container.querySelector<HTMLElement>(".v4-subtab--active") ??
        container.querySelector<HTMLElement>(".v4-chip--active") ??
        container.querySelector<HTMLElement>('[data-subtab-active="true"]');
      if (!active) {
        return;
      }

      const targetLeft = active.offsetLeft - container.clientWidth / 2 + active.clientWidth / 2;
      container.scrollTo({
        left: Math.max(0, targetLeft),
        behavior: "smooth",
      });
    });

    return () => cancelAnimationFrame(frame);
  }, [activeKey]);

  return containerRef;
}
