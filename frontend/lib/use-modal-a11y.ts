"use client";

import { useEffect, type RefObject } from "react";

import { getFocusableElements, handleFocusTrapKeydown } from "@/lib/hive-a11y";

interface UseModalA11yOptions {
  open: boolean;
  onClose: () => void;
  containerRef: RefObject<HTMLElement | null>;
  /** Preferred element to receive focus when opened. */
  initialFocusRef?: RefObject<HTMLElement | null>;
  /** Lock body scroll while open. Defaults to true. */
  lockScroll?: boolean;
}

/** Escape, focus trap, scroll lock, and focus restore for modal surfaces. */
export function useModalA11y({
  open,
  onClose,
  containerRef,
  initialFocusRef,
  lockScroll = true,
}: UseModalA11yOptions): void {
  useEffect(() => {
    if (!open) {
      return;
    }

    const previousActive = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;

    if (lockScroll) {
      document.body.style.overflow = "hidden";
    }

    const focusInitial = (): void => {
      const preferred = initialFocusRef?.current;
      if (preferred) {
        preferred.focus();
        return;
      }
      const container = containerRef.current;
      if (!container) {
        return;
      }
      const [first] = getFocusableElements(container);
      first?.focus();
    };

    const raf = window.requestAnimationFrame(focusInitial);

    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      const container = containerRef.current;
      if (container) {
        handleFocusTrapKeydown(event, container);
      }
    };

    window.addEventListener("keydown", onKeyDown, true);

    return () => {
      window.cancelAnimationFrame(raf);
      if (lockScroll) {
        document.body.style.overflow = previousOverflow;
      }
      window.removeEventListener("keydown", onKeyDown, true);
      previousActive?.focus();
    };
  }, [open, onClose, containerRef, initialFocusRef, lockScroll]);
}
