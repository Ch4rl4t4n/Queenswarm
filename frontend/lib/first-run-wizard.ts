/** Solo first-run wizard — local dismiss (OW5). */

const DISMISS_KEY = "qs_first_run_wizard_dismissed";

function getLocalStorage(): Storage | null {
  if (typeof window !== "undefined" && window.localStorage) {
    return window.localStorage;
  }
  if (typeof globalThis !== "undefined" && "localStorage" in globalThis) {
    return globalThis.localStorage as Storage;
  }
  return null;
}

export function isFirstRunWizardDismissed(): boolean {
  const storage = getLocalStorage();
  if (storage === null) {
    return false;
  }
  return storage.getItem(DISMISS_KEY) === "1";
}

export function dismissFirstRunWizard(): void {
  const storage = getLocalStorage();
  if (storage === null) {
    return;
  }
  storage.setItem(DISMISS_KEY, "1");
}

export function resetFirstRunWizardStateForTests(): void {
  const storage = getLocalStorage();
  if (storage === null) {
    return;
  }
  storage.removeItem(DISMISS_KEY);
}
