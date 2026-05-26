import { describe, expect, it } from "vitest";

import { localizeDescription, localizeNavLabel, localizePhrase } from "@/lib/ui-copy";

describe("ui language policy", () => {
  it("keeps nav and chrome labels in English", () => {
    expect(localizeNavLabel("Settings", "sk")).toBe("Settings");
    expect(localizePhrase("sk", { en: "Save key", sk: "Uložiť kľúč" })).toBe("Save key");
  });

  it("localizes descriptions when SVK is selected", () => {
    expect(
      localizeDescription("sk", {
        en: "Choose which blocks appear on Queen Dashboard.",
        sk: "Vyber, ktoré bloky sa zobrazia na Queen Dashboard.",
      }),
    ).toBe("Vyber, ktoré bloky sa zobrazia na Queen Dashboard.");
    expect(
      localizeDescription("en", {
        en: "Choose which blocks appear on Queen Dashboard.",
        sk: "Vyber, ktoré bloky sa zobrazia na Queen Dashboard.",
      }),
    ).toBe("Choose which blocks appear on Queen Dashboard.");
  });
});
