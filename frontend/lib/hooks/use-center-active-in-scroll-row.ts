"use client";

import { useEffect, useRef } from "react";

import { scrollBehaviorForMotion } from "@/lib/motion-preferences";

/**
 * Keeps the active pill in a horizontal subtab row scrolled to the viewport center.
 *
 * Uses bounding-rect geometry (not `offsetLeft`) so it stays correct even when the
 * active element sits inside a positioned wrapper (e.g. `.hive-subnav-tab-shell`),
 * which would otherwise make `offsetParent` the wrapper and break the math.
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

      // Nothing to center when the row is not horizontally scrollable.
      const maxScroll = container.scrollWidth - container.clientWidth;
      if (maxScroll <= 0) {
        return;
      }

      const containerRect = container.getBoundingClientRect();
      const activeRect = active.getBoundingClientRect();
      const activeCenterWithinContent =
        activeRect.left - containerRect.left + container.scrollLeft + activeRect.width / 2;
      const targetLeft = activeCenterWithinContent - container.clientWidth / 2;
      const clampedLeft = Math.max(0, Math.min(targetLeft, maxScroll));

      container.scrollTo({
        left: clampedLeft,
        behavior: scrollBehaviorForMotion(),
      });
    });

    return () => cancelAnimationFrame(frame);
  }, [activeKey]);

  return containerRef;
}
