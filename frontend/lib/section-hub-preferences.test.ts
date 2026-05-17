import { describe, expect, it } from "vitest";

import {
  readStoredSectionDensity,
  readStoredSectionDensityFromBrowser,
  resolveSectionDensity,
  saveStoredSectionDensity,
  saveStoredSectionDensityFromBrowser,
} from "./section-hub-preferences";

describe("section-hub-preferences", () => {
  it("falls back to comfortable when storage value is missing", () => {
    expect(resolveSectionDensity(null)).toBe("comfortable");
    expect(resolveSectionDensity("")).toBe("comfortable");
  });

  it("accepts compact and comfortable values", () => {
    expect(resolveSectionDensity("compact")).toBe("compact");
    expect(resolveSectionDensity("comfortable")).toBe("comfortable");
  });

  it("falls back to comfortable for unknown values", () => {
    expect(resolveSectionDensity("dense")).toBe("comfortable");
  });

  it("reads density from storage when available", () => {
    const storage = {
      getItem: () => "compact",
    };
    expect(readStoredSectionDensity(storage)).toBe("compact");
  });

  it("falls back to comfortable when storage throws", () => {
    const storage = {
      getItem: () => {
        throw new Error("blocked");
      },
    };
    expect(readStoredSectionDensity(storage)).toBe("comfortable");
  });

  it("writes density to storage when available", () => {
    let saved: string | null = null;
    const storage = {
      setItem: (_key: string, value: string) => {
        saved = value;
      },
    };
    saveStoredSectionDensity(storage, "compact");
    expect(saved).toBe("compact");
  });

  it("does not throw when storage write fails", () => {
    const storage = {
      setItem: () => {
        throw new Error("blocked");
      },
    };
    expect(() => saveStoredSectionDensity(storage, "comfortable")).not.toThrow();
  });

  it("uses comfortable fallback when browser storage is unavailable", () => {
    expect(readStoredSectionDensityFromBrowser()).toBe("comfortable");
    expect(() => saveStoredSectionDensityFromBrowser("compact")).not.toThrow();
  });
});
