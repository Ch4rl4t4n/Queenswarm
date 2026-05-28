/** Anchor popover geometry — Whole-App UI Reorder Phase 12.3 SSOT. */

export interface PopoverPosition {
  top: number;
  left: number;
  width: number;
}

export interface ComputePopoverPositionInput {
  anchorRect: DOMRect;
  panelWidth: number;
  panelHeight: number;
  viewportWidth: number;
  viewportHeight: number;
  viewportMargin?: number;
  triggerGap?: number;
}

/** Place panel below trigger, flip above when needed, clamp to viewport. */
export function computePopoverPosition({
  anchorRect,
  panelWidth,
  panelHeight,
  viewportWidth,
  viewportHeight,
  viewportMargin = 8,
  triggerGap = 8,
}: ComputePopoverPositionInput): PopoverPosition {
  let left = anchorRect.right - panelWidth;
  left = Math.max(viewportMargin, Math.min(left, viewportWidth - panelWidth - viewportMargin));

  let top = anchorRect.bottom + triggerGap;
  if (panelHeight > 0 && top + panelHeight > viewportHeight - viewportMargin) {
    top = anchorRect.top - triggerGap - panelHeight;
  }
  if (top < viewportMargin) {
    top = anchorRect.bottom + triggerGap;
  }

  return { top, left, width: panelWidth };
}

export function popoverPanelWidthPx(viewportWidth: number, preferredWidth = 320): number {
  return Math.min(preferredWidth, viewportWidth * 0.85);
}
