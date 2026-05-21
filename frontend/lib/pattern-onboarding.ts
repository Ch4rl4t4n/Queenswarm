/** Pattern onboarding UX — local dismiss state (dashboard banner). */

export const PATTERN_ONBOARDING_TARGET = 5;

const DISMISS_KEY = "qs_pattern_onboarding_dismissed";

function getLocalStorage(): Storage | null {
  if (typeof window !== "undefined" && window.localStorage) {
    return window.localStorage;
  }
  if (typeof globalThis !== "undefined" && "localStorage" in globalThis) {
    return globalThis.localStorage as Storage;
  }
  return null;
}

export function isPatternOnboardingDismissed(): boolean {
  const storage = getLocalStorage();
  if (storage === null) {
    return false;
  }
  return storage.getItem(DISMISS_KEY) === "1";
}

export function dismissPatternOnboarding(): void {
  const storage = getLocalStorage();
  if (storage === null) {
    return;
  }
  storage.setItem(DISMISS_KEY, "1");
}

export function patternProgressPct(uniqueCount: number, target = PATTERN_ONBOARDING_TARGET): number {
  if (target <= 0) {
    return 0;
  }
  return Math.min(100, Math.round((Math.max(0, uniqueCount) / target) * 100));
}

export function resetPatternOnboardingStateForTests(): void {
  const storage = getLocalStorage();
  if (storage === null) {
    return;
  }
  storage.removeItem(DISMISS_KEY);
}
