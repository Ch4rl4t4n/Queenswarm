"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import { createPortal } from "react-dom";

import {
  computePopoverPosition,
  popoverPanelWidthPx,
  type PopoverPosition,
} from "@/lib/hive-popover-position";
import { useModalA11y } from "@/lib/use-modal-a11y";
import { cn } from "@/lib/utils";

export type HivePopoverPresentation = "anchor" | "flyout";

export interface HivePopoverShellProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  /** anchor = portaled near trigger; flyout = fixed drawer + backdrop (CSS positions panel). */
  presentation?: HivePopoverPresentation;
  anchorRef?: RefObject<HTMLElement | null>;
  ignoreOutsideRefs?: Array<RefObject<HTMLElement | null>>;
  ignoreOutsideSelector?: string;
  panelClassName?: string;
  labelledBy?: string;
  describedBy?: string;
  ariaLabel?: string;
  initialFocusRef?: RefObject<HTMLElement | null>;
  preferredWidth?: number;
  viewportMargin?: number;
  triggerGap?: number;
  backdropClassName?: string;
}

/**
 * Portaled popover / flyout shell — Escape, focus trap, outside dismiss.
 * Whole-App UI Reorder Phase 12.3 (InfoHint anchor + dashboard layout flyout).
 */
export function HivePopoverShell({
  open,
  onClose,
  children,
  presentation = "anchor",
  anchorRef,
  ignoreOutsideRefs = [],
  ignoreOutsideSelector,
  panelClassName,
  labelledBy,
  describedBy,
  ariaLabel,
  initialFocusRef,
  preferredWidth = 320,
  viewportMargin = 8,
  triggerGap = 8,
  backdropClassName,
}: HivePopoverShellProps): ReactNode {
  const panelRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);
  const [panelStyle, setPanelStyle] = useState<PopoverPosition | null>(null);

  useModalA11y({
    open,
    onClose,
    containerRef: panelRef,
    initialFocusRef,
    lockScroll: false,
  });

  useEffect(() => {
    setMounted(true);
  }, []);

  const updatePosition = useCallback(() => {
    if (presentation !== "anchor") {
      return;
    }
    const anchor = anchorRef?.current;
    if (!anchor) {
      return;
    }
    const panel = panelRef.current;
    const width = popoverPanelWidthPx(window.innerWidth, preferredWidth);
    const height = panel?.offsetHeight ?? 0;
    setPanelStyle(
      computePopoverPosition({
        anchorRect: anchor.getBoundingClientRect(),
        panelWidth: width,
        panelHeight: height,
        viewportWidth: window.innerWidth,
        viewportHeight: window.innerHeight,
        viewportMargin,
        triggerGap,
      }),
    );
  }, [anchorRef, presentation, preferredWidth, triggerGap, viewportMargin]);

  useLayoutEffect(() => {
    if (!open || presentation !== "anchor") {
      setPanelStyle(null);
      return;
    }
    updatePosition();
  }, [open, presentation, updatePosition, children]);

  useLayoutEffect(() => {
    if (!open || presentation !== "anchor" || !panelRef.current) {
      return;
    }
    updatePosition();
  }, [open, presentation, panelStyle?.width, updatePosition]);

  useEffect(() => {
    if (!open || presentation !== "anchor") {
      return;
    }
    const onScrollOrResize = (): void => {
      updatePosition();
    };
    window.addEventListener("scroll", onScrollOrResize, true);
    window.addEventListener("resize", onScrollOrResize);
    return () => {
      window.removeEventListener("scroll", onScrollOrResize, true);
      window.removeEventListener("resize", onScrollOrResize);
    };
  }, [open, presentation, updatePosition]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onClickAway = (event: MouseEvent): void => {
      const target = event.target as Node;
      if (panelRef.current?.contains(target)) {
        return;
      }
      for (const ref of ignoreOutsideRefs) {
        if (ref.current?.contains(target)) {
          return;
        }
      }
      if (ignoreOutsideSelector) {
        const el = event.target as HTMLElement | null;
        if (el?.closest?.(ignoreOutsideSelector)) {
          return;
        }
      }
      onClose();
    };
    const timer = window.setTimeout(() => {
      window.addEventListener("mousedown", onClickAway);
    }, 0);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("mousedown", onClickAway);
    };
  }, [open, onClose, ignoreOutsideRefs, ignoreOutsideSelector]);

  if (!open || !mounted) {
    return null;
  }

  const anchorWidth = popoverPanelWidthPx(typeof window !== "undefined" ? window.innerWidth : preferredWidth, preferredWidth);

  const panel = (
    <div
      ref={panelRef}
      role="dialog"
      aria-modal="true"
      tabIndex={-1}
      aria-labelledby={labelledBy}
      aria-describedby={describedBy}
      aria-label={labelledBy ? undefined : ariaLabel}
      className={cn(presentation === "anchor" && !panelStyle && "invisible", panelClassName)}
      style={
        presentation === "anchor"
          ? panelStyle
            ? { top: panelStyle.top, left: panelStyle.left, width: panelStyle.width }
            : { top: 0, left: 0, width: anchorWidth }
          : undefined
      }
    >
      {children}
    </div>
  );

  if (presentation === "flyout") {
    return createPortal(
      <>
        <div className={backdropClassName} aria-hidden onClick={onClose} />
        {panel}
      </>,
      document.body,
    );
  }

  return createPortal(panel, document.body);
}
