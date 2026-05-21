import { describe, expect, it, beforeEach } from "vitest";

import {
  dismissPatternOnboarding,
  isPatternOnboardingDismissed,
  patternProgressPct,
  resetPatternOnboardingStateForTests,
} from "@/lib/pattern-onboarding";

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

describe("pattern-onboarding", () => {
  beforeEach(() => {
    installLocalStorageMock();
    resetPatternOnboardingStateForTests();
  });

  it("patternProgressPct caps at 100", () => {
    expect(patternProgressPct(0)).toBe(0);
    expect(patternProgressPct(3, 5)).toBe(60);
    expect(patternProgressPct(5, 5)).toBe(100);
    expect(patternProgressPct(9, 5)).toBe(100);
  });

  it("dismiss persists in localStorage", () => {
    expect(isPatternOnboardingDismissed()).toBe(false);
    dismissPatternOnboarding();
    expect(isPatternOnboardingDismissed()).toBe(true);
  });
});
