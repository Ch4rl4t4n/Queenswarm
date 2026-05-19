/** localStorage keys for PWA install prompt (mobile/tablet only). */

export const PWA_VISIT_KEY = "qs_pwa_visits";
export const PWA_DISMISS_KEY = "qs_pwa_install_dismissed";
export const PWA_SESSION_BUMP_KEY = "qs_pwa_visit_bumped";

export const PWA_MIN_VISITS = 2;
export const PWA_DISMISS_MS = 30 * 24 * 60 * 60 * 1000;

/** True when app runs as installed PWA (standalone display mode). */
export function isStandalonePwa(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  if (window.matchMedia("(display-mode: standalone)").matches) {
    return true;
  }
  const nav = window.navigator as Navigator & { standalone?: boolean };
  return nav.standalone === true;
}

/** iOS Safari has no beforeinstallprompt — show manual steps. */
export function isIosSafari(userAgent?: string, maxTouchPoints?: number): boolean {
  const ua = userAgent ?? (typeof navigator !== "undefined" ? navigator.userAgent : "");
  const touch = maxTouchPoints ?? (typeof navigator !== "undefined" ? navigator.maxTouchPoints : 0);
  const isIos =
    /iPad|iPhone|iPod/.test(ua) ||
    (typeof navigator !== "undefined" && navigator.platform === "MacIntel" && touch > 1);
  const isSafari = /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS|Chrome/.test(ua);
  return isIos && isSafari;
}

export function readVisitCount(storage?: Pick<Storage, "getItem">): number {
  const raw = storage?.getItem(PWA_VISIT_KEY) ?? null;
  if (!raw) {
    return 0;
  }
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
}

/** Bump visit counter once per browser session. Returns new total. */
export function bumpVisitCount(
  session: Pick<Storage, "getItem" | "setItem">,
  local: Pick<Storage, "getItem" | "setItem">,
): number {
  if (session.getItem(PWA_SESSION_BUMP_KEY) === "1") {
    return readVisitCount(local);
  }
  const next = readVisitCount(local) + 1;
  local.setItem(PWA_VISIT_KEY, String(next));
  session.setItem(PWA_SESSION_BUMP_KEY, "1");
  return next;
}

export function isInstallDismissed(storage?: Pick<Storage, "getItem">, nowMs = Date.now()): boolean {
  const raw = storage?.getItem(PWA_DISMISS_KEY) ?? null;
  if (!raw) {
    return false;
  }
  const dismissedUntil = Number.parseInt(raw, 10);
  if (!Number.isFinite(dismissedUntil)) {
    return false;
  }
  return nowMs < dismissedUntil;
}

export function dismissInstallPrompt(storage?: Pick<Storage, "setItem">, nowMs = Date.now()): void {
  storage?.setItem(PWA_DISMISS_KEY, String(nowMs + PWA_DISMISS_MS));
}

export function shouldOfferInstallPrompt(input: {
  belowDesktop: boolean;
  standalone: boolean;
  dismissed: boolean;
  visits: number;
  pathname: string;
}): boolean {
  if (!input.belowDesktop || input.standalone || input.dismissed) {
    return false;
  }
  if (input.visits < PWA_MIN_VISITS) {
    return false;
  }
  if (
    input.pathname.startsWith("/login") ||
    input.pathname.startsWith("/verify-2fa") ||
    input.pathname === "/offline"
  ) {
    return false;
  }
  return true;
}
