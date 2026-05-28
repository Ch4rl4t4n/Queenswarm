"use client";

import { useRef, type ReactNode, type RefObject } from "react";

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

  return (
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
}
