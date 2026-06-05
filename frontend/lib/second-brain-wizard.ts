/** Second Brain Pack wizard — local dismiss. */

const DISMISS_KEY = "qs_second_brain_wizard_dismissed";

function getLocalStorage(): Storage | null {
  if (typeof window !== "undefined" && window.localStorage) {
    return window.localStorage;
  }
  if (typeof globalThis !== "undefined" && "localStorage" in globalThis) {
    return globalThis.localStorage as Storage;
  }
  return null;
}

export function isSecondBrainWizardDismissed(): boolean {
  const storage = getLocalStorage();
  if (storage === null) {
    return false;
  }
  return storage.getItem(DISMISS_KEY) === "1";
}

export function dismissSecondBrainWizard(): void {
  const storage = getLocalStorage();
  if (storage === null) {
    return;
  }
  storage.setItem(DISMISS_KEY, "1");
}
