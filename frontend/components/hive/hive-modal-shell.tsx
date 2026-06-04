"use client";

import { useEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import { createPortal } from "react-dom";

import { useModalA11y } from "@/lib/use-modal-a11y";
import { cn } from "@/lib/utils";

export type HiveModalAlign = "center" | "bottom-sheet" | "drawer-right";

/** Overlay flex alignment — mobile bottom sheet, centered from sm+, or right drawer. */
export function hiveModalOverlayAlignClass(align: HiveModalAlign): string {
  if (align === "bottom-sheet") {
    return "items-end justify-center p-0 sm:items-center sm:p-4";
  }
  if (align === "drawer-right") {
    return "items-stretch justify-end p-0";
  }
  return "items-center justify-center p-4";
}

/** Shared scroll body for HiveModalShell report dialogs. */
export const hiveModalScrollBodyClass =
  "hive-modal-scroll hive-scrollbar min-h-0 flex-1 px-4 py-4 sm:px-5";

/** Shared panel chrome for bottom-sheet modals (max-width/height set per dialog). */
export const hiveModalBottomSheetPanelClass =
  "qs-bubble flex w-full flex-col overflow-hidden rounded-t-(--qs-radius-lg) sm:rounded-(--qs-radius-lg)";

interface HiveModalShellProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  /** Dialog panel class names (width, padding, border…). */
  panelClassName?: string;
  /** Fixed overlay wrapper — extra classes merged after align preset. */
  overlayClassName?: string;
  labelledBy?: string;
  describedBy?: string;
  /** Use when no visible title element exists. */
  ariaLabel?: string;
  align?: HiveModalAlign;
  zIndexClass?: "z-50" | "z-[60]" | "z-[70]" | "z-[72]" | "z-[75]" | "z-[220]";
  backdropClassName?: string;
  initialFocusRef?: RefObject<HTMLElement | null>;
  lockScroll?: boolean;
  closeLabel?: string;
}

/**
 * Accessible modal shell — backdrop dismiss, Escape, focus trap, scroll lock.
 * Whole-App UI Reorder Phase 7.3 standard for bespoke dialogs.
 */
export function HiveModalShell({
  open,
  onClose,
  children,
  panelClassName,
  overlayClassName,
  labelledBy,
  describedBy,
  ariaLabel,
  align = "center",
  zIndexClass = "z-50",
  backdropClassName = "bg-black/75",
  initialFocusRef,
  lockScroll = true,
  closeLabel = "Close dialog",
}: HiveModalShellProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useModalA11y({
    open,
    onClose,
    containerRef: dialogRef,
    initialFocusRef,
    lockScroll,
  });

  if (!open) {
    return null;
  }

  const modal = (
    <div
      className={cn("fixed inset-0 flex", hiveModalOverlayAlignClass(align), zIndexClass, overlayClassName)}
      role="presentation"
    >
      <button
        type="button"
        className={cn("absolute inset-0", backdropClassName)}
        aria-label={closeLabel}
        onClick={onClose}
      />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        tabIndex={-1}
        aria-labelledby={labelledBy}
        aria-describedby={describedBy}
        aria-label={labelledBy ? undefined : ariaLabel}
        className={cn("relative", panelClassName)}
        onClick={(event) => event.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );

  if (!mounted || typeof document === "undefined") {
    return null;
  }

  return createPortal(modal, document.body);
}
