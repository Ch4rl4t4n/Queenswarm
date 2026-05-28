/**
 * Whole-App UI Reorder — shared accessibility helpers (Phase 7).
 */

/** Main canvas id — target for skip link and landmark focus. */
export const HIVE_MAIN_CONTENT_ID = "hive-main-canvas";

/** Selector for keyboard-focusable elements inside a container. */
export const HIVE_FOCUSABLE_SELECTOR =
  'a[href]:not([tabindex="-1"]), button:not([disabled]):not([tabindex="-1"]), textarea:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

function isVisible(element: HTMLElement): boolean {
  if (element.getAttribute("aria-hidden") === "true") {
    return false;
  }
  const style = window.getComputedStyle(element);
  return style.visibility !== "hidden" && style.display !== "none";
}

/** Collect visible, tabbable elements within a root node. */
export function getFocusableElements(root: HTMLElement): HTMLElement[] {
  return Array.from(root.querySelectorAll<HTMLElement>(HIVE_FOCUSABLE_SELECTOR)).filter((element) => {
    if (!isVisible(element)) {
      return false;
    }
    if (element.closest("[inert]")) {
      return false;
    }
    return true;
  });
}

/** Focusable subnav tab targets inside a pill row. */
export const HIVE_SUBNAV_TAB_SELECTOR = "[data-hive-subnav-tab]:not([aria-disabled='true'])";

/** Collect enabled subnav tabs within a nav row. */
export function getSubnavTabs(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(HIVE_SUBNAV_TAB_SELECTOR)).filter((element) => {
    if (element.closest(".hive-subnav-tab-shell--disabled")) {
      return false;
    }
    return isVisible(element);
  });
}

/** Resolve which tab is active inside a subnav row (focus or aria-current). */
export function resolveActiveSubnavIndex(tabs: HTMLElement[]): number {
  const active = document.activeElement as HTMLElement | null;
  let index = tabs.findIndex((tab) => tab === active || (active !== null && tab.contains(active)));
  if (index < 0) {
    index = tabs.findIndex((tab) => tab.getAttribute("aria-current") === "page");
  }
  return index < 0 ? 0 : index;
}

/** Arrow / Home / End navigation for horizontal pill subnav rows. */
export function handleHorizontalNavKeydown(
  event: KeyboardEvent,
  container: HTMLElement,
  onActivate?: (tab: HTMLElement) => void,
): void {
  const key = event.key;
  if (key !== "ArrowLeft" && key !== "ArrowRight" && key !== "Home" && key !== "End") {
    return;
  }

  const tabs = getSubnavTabs(container);
  if (tabs.length === 0) {
    return;
  }

  const index = resolveActiveSubnavIndex(tabs);
  let nextIndex = index;

  switch (key) {
    case "ArrowLeft":
      nextIndex = index <= 0 ? tabs.length - 1 : index - 1;
      break;
    case "ArrowRight":
      nextIndex = index >= tabs.length - 1 ? 0 : index + 1;
      break;
    case "Home":
      nextIndex = 0;
      break;
    case "End":
      nextIndex = tabs.length - 1;
      break;
    default:
      return;
  }

  event.preventDefault();
  const next = tabs[nextIndex];
  next.focus();
  onActivate?.(next);
}

/** Cycle Tab / Shift+Tab within a modal container (WAI-ARIA dialog pattern). */
export function handleFocusTrapKeydown(event: KeyboardEvent, container: HTMLElement): void {
  if (event.key !== "Tab") {
    return;
  }
  const focusable = getFocusableElements(container);
  if (focusable.length === 0) {
    event.preventDefault();
    container.focus();
    return;
  }

  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  const active = document.activeElement as HTMLElement | null;

  if (event.shiftKey) {
    if (!active || active === first || !container.contains(active)) {
      event.preventDefault();
      last.focus();
    }
    return;
  }

  if (active === last) {
    event.preventDefault();
    first.focus();
  }
}
