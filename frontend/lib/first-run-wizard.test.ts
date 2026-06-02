import { describe, expect, it, beforeEach } from "vitest";

import {
  dismissFirstRunWizard,
  isFirstRunWizardDismissed,
  resetFirstRunWizardStateForTests,
} from "@/lib/first-run-wizard";

function installLocalStorageMock(): void {
  const store = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => {
        store.set(key, value);
      },
      removeItem: (key: string) => {
        store.delete(key);
      },
      clear: () => {
        store.clear();
      },
    },
  });
}

describe("first-run-wizard", () => {
  beforeEach(() => {
    installLocalStorageMock();
    resetFirstRunWizardStateForTests();
  });

  it("dismiss persists in localStorage", () => {
    expect(isFirstRunWizardDismissed()).toBe(false);
    dismissFirstRunWizard();
    expect(isFirstRunWizardDismissed()).toBe(true);
  });
});
